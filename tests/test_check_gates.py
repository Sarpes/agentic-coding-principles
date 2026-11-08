"""Tests for the stage gate (check_gates.py). Real temporary git repositories are built where history matters."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "agentic-principles" / "scripts"))

import check_gates  # noqa: E402
from check_gates import (  # noqa: E402
    SOURCE_EXTENSIONS,
    STAGE_NAMES,
    TRUST_LIMIT,
    Override,
    Problem,
    Row,
    check_project,
    evidence_content_problems,
    main,
    override_problems,
    parse_overrides,
    parse_stages,
    stage_problems,
    tracked_files,
)

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com", GIT_TERMINAL_PROMPT="0")


def git(root, *args):
    result = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
                             "-C", str(root), *args],
                            capture_output=True, text=True, encoding="utf-8", env=GIT_ENV)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def write(root, name, content):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def commit(root, files=None, message="c", remove=()):
    """Write files, stage exactly those, commit, and return the new commit hash."""
    for name, content in (files or {}).items():
        write(root, name, content)
        git(root, "add", "--", name)
    for name in remove:
        git(root, "rm", "-q", "--", name)
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def ls(root):
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def row(n, status, evidence="", override="-"):
    return n, f"| {STAGE_NAMES[n]} | {status} | {evidence} | {override} |"


def table(*rows, size="small", method="normal", extra=()):
    given = dict(rows)
    body = [given.get(n) or f"| {STAGE_NAMES[n]} | open | - | - |" for n in range(8)]
    head = [f"Size: {size}", f"Method: {method}", *extra, "",
            "| Stage | Status | Evidence | Override |", "|---|---|---|---|"]
    return "\n".join(head + body) + "\n"


def line_of(text, needle):
    for number, line in enumerate(text.split("\n"), start=1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} not in text")


def messages(problems):
    return [p.message for p in problems]


REQ_OK = "# Requirements\n\n| ID | Requirement |\n|---|---|\n| REQ-1 | The tool works |\n"
ATTACKS_OK = "# Attacks\n\n- ATK-1 feed it garbage\n"
DECISIONS_OK = "# Decisions\n\n### D1. Pick a store\n\n- **Context:** text\n"
LEDGER_OK = ("# Build ledger\n\n## Reviews\n\n| Task | Reviewer | Result |\n|---|---|---|\n"
             "| 1 | fresh session | approved |\n")
LEDGER_NO_ROWS = "# Build ledger\n\n## Reviews\n\n| Task | Reviewer | Result |\n|---|---|---|\n"
AI_OK = "# AI log\n\n### 1. Title\n\n## Retro\n\nThree mistakes became two rules and one template change.\n"
AI_EMPTY_RETRO = "# AI log\n\n### 1. Title\n\n## Retro\n\n<!-- write the retro here -->\n"
STAGES_OPEN = table()


class GitCase(unittest.TestCase):
    def make_repo(self, files=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "proj"
        root.mkdir()
        git(root, "init", "-q")
        commit(root, files or {"README.md": "# project\n"}, "initial")
        return root

    def assert_mentions(self, problems, needle):
        self.assertTrue(any(needle in m for m in messages(problems)),
                        f"no problem mentions {needle!r}: {problems}")


# ---------------------------------------------------------------- stage table

class StageRules(GitCase):
    def setUp(self):
        self.root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK,
                                    "DECISIONS.md": DECISIONS_OK, "README.md": "# project\n"})

    def check(self, text, overrides=None):
        return stage_problems(text, self.root, ls(self.root), overrides or {})

    def stage0(self, evidence):
        return table(row(0, "passed", evidence))

    def test_all_open_table_passes(self):
        self.assertEqual(self.check(STAGES_OPEN), [])

    def test_passed_without_evidence_fires(self):
        self.assert_mentions(self.check(self.stage0("")), "evidence")

    def test_dash_is_no_evidence(self):
        self.assert_mentions(self.check(self.stage0("-")), "evidence")

    def test_missing_file_is_named(self):
        self.assert_mentions(self.check(self.stage0("file:nope.md")), "nope.md")

    def test_complete_stage_0_passes(self):
        self.assertEqual(self.check(self.stage0("file:REQUIREMENTS.md,file:ATTACKS.md")), [])

    def test_spaces_after_the_comma_are_fine(self):
        self.assertEqual(self.check(self.stage0("file:REQUIREMENTS.md, file:ATTACKS.md")), [])

    def test_missing_required_file_is_named(self):
        self.assert_mentions(self.check(self.stage0("file:REQUIREMENTS.md")), "ATTACKS.md")

    def test_stages_file_is_not_evidence(self):
        write(self.root, "STAGES.md", STAGES_OPEN)
        git(self.root, "add", "STAGES.md")
        self.assert_mentions(self.check(self.stage0("file:STAGES.md,file:ATTACKS.md")), "STAGES.md")

    def test_overrides_file_is_not_evidence(self):
        commit(self.root, {"OVERRIDES.md": "# Overrides\n"})
        self.assert_mentions(self.check(self.stage0("file:OVERRIDES.md,file:ATTACKS.md")), "OVERRIDES.md")

    def test_folder_is_refused(self):
        commit(self.root, {"docs/a.md": "text\n"})
        self.assert_mentions(self.check(self.stage0("file:docs,file:ATTACKS.md")), "folder")

    def test_untracked_file_is_refused(self):
        write(self.root, "loose.md", "REQ-1\n")
        self.assert_mentions(self.check(self.stage0("file:loose.md,file:ATTACKS.md")), "tracked")

    def test_example_marker_is_refused(self):
        commit(self.root, {"REQUIREMENTS.md": "REQ-1 (EXAMPLE) replace me\n"})
        self.assert_mentions(self.check(self.stage0("file:REQUIREMENTS.md,file:ATTACKS.md")), "(EXAMPLE)")

    def test_path_outside_the_project_is_refused_without_reading(self):
        problems = self.check(self.stage0("file:../../secret.txt,file:ATTACKS.md"))
        self.assert_mentions(problems, "outside")

    def test_absolute_path_outside_is_refused(self):
        outside = str(Path(self.root).parent.resolve() / "x.txt").replace("\\", "/")
        self.assert_mentions(self.check(self.stage0(f"file:{outside}")), "outside")

    def test_backslash_path_is_read_as_a_path(self):
        commit(self.root, {"docs/a.md": "text\n"})
        problems = self.check(self.stage0(r"file:docs\a.md,file:REQUIREMENTS.md,file:ATTACKS.md"))
        self.assertEqual(problems, [])

    def test_zero_byte_file_is_refused(self):
        commit(self.root, {"ATTACKS.md": b""})
        self.assert_mentions(self.check(self.stage0("file:REQUIREMENTS.md,file:ATTACKS.md")), "empty")

    def test_unknown_evidence_kind_is_refused(self):
        self.assert_mentions(self.check(self.stage0("doc:thing")), "file:")

    def test_commit_head_is_not_a_hash(self):
        self.assert_mentions(self.check(table(row(3, "passed", "commit:HEAD"))), "hexadecimal")

    def test_commit_on_another_branch_is_not_history(self):
        branch = git(self.root, "rev-parse", "--abbrev-ref", "HEAD")
        git(self.root, "checkout", "-q", "-b", "side")
        other = commit(self.root, {"side.txt": "x\n"}, "side work")
        git(self.root, "checkout", "-q", branch)
        self.assert_mentions(self.check(table(row(3, "passed", f"commit:{other}"))), "history")

    def test_unknown_but_well_formed_hash_is_not_history(self):
        self.assert_mentions(self.check(table(row(3, "passed", "commit:" + "a" * 40))), "history")

    def test_build_stage_after_closed_earlier_stages_passes(self):
        commit(self.root, {"STAGES.md": STAGES_OPEN}, "setup")
        later = commit(self.root, {"BUILD-LEDGER.md": LEDGER_OK, "app.py": "x = 1\n"}, "work")
        overrides = {"O1": Override("open", "0 Intake", "-"), "O2": Override("open", "1 Design", "-"),
                     "O3": Override("open", "2 Plan", "-")}
        text = table(row(0, "overridden", "", "O1"), row(1, "overridden", "", "O2"),
                     row(2, "overridden", "", "O3"),
                     row(3, "passed", f"commit:{later},file:BUILD-LEDGER.md"))
        self.assertEqual(self.check(text, overrides), [])

    def test_overridden_with_unknown_override_names_it(self):
        self.assert_mentions(self.check(table(row(0, "overridden", "", "O1"))), "O1")

    def test_overridden_without_an_override_id_fires(self):
        self.assert_mentions(self.check(table(row(0, "overridden", "", "-"))), "Override")

    def test_override_for_another_stage_fires(self):
        problems = self.check(table(row(1, "overridden", "", "O1")), {"O1": Override("open", "0 Intake", "-")})
        self.assert_mentions(problems, "stage")

    def test_closed_override_does_not_silence(self):
        problems = self.check(table(row(0, "overridden", "", "O1")), {"O1": Override("closed", "0 Intake", "-")})
        self.assert_mentions(problems, "closed")

    def test_open_override_for_its_stage_passes(self):
        problems = self.check(table(row(0, "overridden", "", "O1")), {"O1": Override("open", "0 Intake", "-")})
        self.assertEqual(problems, [])

    def test_closed_stage_after_open_stage_fires_at_its_row(self):
        text = table(row(0, "open"), row(1, "passed", "file:DECISIONS.md"))
        problems = self.check(text)
        self.assert_mentions(problems, "earlier")
        hit = [p for p in problems if "earlier" in p.message][0]
        self.assertEqual(hit.line, line_of(text, "1 Design"))

    def test_invalid_size_fires(self):
        self.assert_mentions(self.check(table(size="huge")), "Size")

    def test_invalid_method_fires(self):
        self.assert_mentions(self.check(table(method="magic")), "Method")

    def test_missing_size_line_fires(self):
        self.assert_mentions(self.check(table().replace("Size: small\n", "")), "Size")

    def test_unknown_status_fires_at_its_row(self):
        text = table(row(0, "done"))
        problems = self.check(text)
        self.assert_mentions(problems, "done")
        self.assertEqual(problems[0].line, line_of(text, "0 Intake"))

    def test_missing_stage_row_fires(self):
        text = table().replace("| 7 Retro | open | - | - |\n", "")
        self.assert_mentions(self.check(text), "7 Retro")

    def test_duplicate_stage_row_fires(self):
        text = table() + "| 7 Retro | open | - | - |\n"
        self.assert_mentions(self.check(text), "7 Retro")

    def test_no_table_fires(self):
        self.assert_mentions(self.check("Size: small\nMethod: normal\n"), "table")

    def test_crlf_and_bom_change_nothing(self):
        text = self.stage0("file:REQUIREMENTS.md")
        plain = self.check(text)
        self.assertTrue(plain)
        self.assertEqual(self.check("﻿" + text.replace("\n", "\r\n")), plain)

    def test_table_inside_a_comment_is_ignored(self):
        text = "<!--\n" + table(row(0, "passed")) + "-->\n" + STAGES_OPEN
        self.assertEqual(self.check(text), [])


class AdoptionRules(GitCase):
    def adopted_table(self, n, *adopted_stages, extra=None):
        extra = [f"Adopted-at: {n}"] if extra is None else extra
        rows = [row(s, "adopted") for s in adopted_stages]
        return table(*rows, extra=extra)

    def project(self, with_source=True, stages_text=None):
        root = self.make_repo({"README.md": "# p\n"})
        if with_source:
            commit(root, {"app.py": "x = 1\n"}, "code")
        commit(root, {"STAGES.md": stages_text if stages_text is not None else self.adopted_table(2, 0, 1)},
               "stages")
        return root

    def test_adoption_with_prior_source_passes(self):
        root = self.project()
        self.assertEqual(stage_problems(self.adopted_table(2, 0, 1), root, ls(root), {}), [])

    def test_adopted_without_adopted_at_fires(self):
        root = self.project(stages_text=STAGES_OPEN)
        text = self.adopted_table(0, 0, extra=[])
        self.assertTrue(any("Adopted-at" in m for m in messages(stage_problems(text, root, ls(root), {}))))

    def test_adopted_at_or_above_n_fires(self):
        root = self.project()
        text = self.adopted_table(2, 0, 1, 2)
        problems = stage_problems(text, root, ls(root), {})
        self.assertTrue(any("Adopted-at" in m for m in messages(problems)))
        self.assertEqual([p.line for p in problems if "Adopted-at" in p.message],
                         [line_of(text, "2 Plan")])

    def test_adopted_at_added_after_first_commit_fires(self):
        root = self.project(stages_text=STAGES_OPEN)
        problems = stage_problems(self.adopted_table(2, 0, 1), root, ls(root), {})
        self.assertTrue(any("first commit" in m for m in messages(problems)))

    def test_adopted_at_changed_after_first_commit_fires(self):
        root = self.project(stages_text=self.adopted_table(1, 0))
        problems = stage_problems(self.adopted_table(5, 0, 1, 2, 3, 4), root, ls(root), {})
        self.assertTrue(any("first commit" in m for m in messages(problems)))

    def test_brand_new_repo_cannot_claim_adoption(self):
        root = self.project(with_source=False)
        problems = stage_problems(self.adopted_table(2, 0, 1), root, ls(root), {})
        self.assertTrue(any("source" in m for m in messages(problems)))

    def test_adopted_at_above_five_fires(self):
        root = self.project(stages_text=self.adopted_table(6, 0))
        problems = stage_problems(self.adopted_table(6, 0), root, ls(root), {})
        self.assertTrue(any("at most 5" in m for m in messages(problems)))

    def test_adopted_at_five_is_allowed(self):
        root = self.project(stages_text=self.adopted_table(5, 0, 1, 2, 3, 4))
        self.assertEqual(stage_problems(self.adopted_table(5, 0, 1, 2, 3, 4), root, ls(root), {}), [])

    def test_uncommitted_stages_file_asks_for_a_commit(self):
        root = self.make_repo({"app.py": "x = 1\n"})
        problems = stage_problems(self.adopted_table(2, 0, 1), root, ls(root), {})
        self.assertTrue(any("commit" in m for m in messages(problems)))

    def test_source_in_the_same_commit_as_stages_does_not_count(self):
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"app.py": "x = 1\n", "STAGES.md": self.adopted_table(2, 0, 1)}, "both")
        problems = stage_problems(self.adopted_table(2, 0, 1), root, ls(root), {})
        self.assertTrue(any("source" in m for m in messages(problems)))

    def test_reopened_stage_6_with_stage_7_passed_is_fine(self):
        root = self.make_repo({"AI-Agents.md": AI_OK})
        text = table(row(6, "reopened"), row(7, "passed", "file:AI-Agents.md"),
                     row(0, "overridden", "", "O1"), row(1, "overridden", "", "O1"),
                     row(2, "overridden", "", "O1"), row(3, "overridden", "", "O1"),
                     row(4, "overridden", "", "O1"), row(5, "overridden", "", "O1"))
        overrides = {"O1": Override("open", "0 Intake", "-")}
        problems = stage_problems(text, root, ls(root), overrides)
        self.assertFalse(any("reopened" in m or "earlier" in m for m in messages(problems)), problems)

    def test_reopened_stage_5_fires(self):
        root = self.make_repo()
        self.assertTrue(any("reopened" in m for m in messages(
            stage_problems(table(row(5, "reopened")), root, ls(root), {}))))


# ------------------------------------------------------------ evidence content

class EvidenceRules(GitCase):
    def run_check(self, root, stage, size, evidence, first=None):
        r = Row(10, STAGE_NAMES[stage], "passed", evidence, "-")
        return evidence_content_problems(stage, size, root, ls(root), r, first)

    def test_stage_0_requirements_without_req_id_fires(self):
        root = self.make_repo({"REQUIREMENTS.md": "# Requirements\n\nnothing numbered\n", "ATTACKS.md": ATTACKS_OK})
        self.assert_mentions(self.run_check(root, 0, "small", "file:REQUIREMENTS.md,file:ATTACKS.md"), "REQ")

    def test_stage_0_req_id_in_a_comment_does_not_count(self):
        root = self.make_repo({"REQUIREMENTS.md": "<!-- REQ-1 -->\n", "ATTACKS.md": ATTACKS_OK})
        self.assert_mentions(self.run_check(root, 0, "small", "file:REQUIREMENTS.md,file:ATTACKS.md"), "REQ")

    def test_stage_0_with_req_id_passes(self):
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK})
        self.assertEqual(self.run_check(root, 0, "small", "file:REQUIREMENTS.md,file:ATTACKS.md"), [])

    def test_stage_1_decisions_without_entry_fires(self):
        root = self.make_repo({"DECISIONS.md": "# Decisions\n"})
        self.assert_mentions(self.run_check(root, 1, "small", "file:DECISIONS.md"), "entry")

    def test_stage_1_small_with_entry_passes(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK})
        self.assertEqual(self.run_check(root, 1, "small", "file:DECISIONS.md"), [])

    def test_stage_1_full_needs_a_design_file(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK})
        self.assert_mentions(self.run_check(root, 1, "full", "file:DECISIONS.md"), "design")

    def test_stage_1_full_plan_file_is_not_a_design(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/plans/p.md": "plan\n"})
        self.assert_mentions(self.run_check(root, 1, "full", "file:DECISIONS.md,file:docs/plans/p.md"), "design")

    def test_stage_1_full_with_design_passes(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/design.md": "design\n"})
        self.assertEqual(self.run_check(root, 1, "full", "file:DECISIONS.md,file:docs/design.md"), [])

    def test_stage_2_full_plan_outside_docs_plans_fires(self):
        root = self.make_repo({"docs/plan.md": "plan\n"})
        self.assert_mentions(self.run_check(root, 2, "full", "file:docs/plan.md"), "docs/plans")

    def test_stage_2_full_plan_in_docs_plans_passes(self):
        root = self.make_repo({"docs/plans/p.md": "plan\n"})
        self.assertEqual(self.run_check(root, 2, "full", "file:docs/plans/p.md"), [])

    def test_stage_2_small_needs_plan_md(self):
        root = self.make_repo({"docs/plans/p.md": "plan\n", "PLAN.md": "tasks\n"})
        self.assert_mentions(self.run_check(root, 2, "small", "file:docs/plans/p.md"), "PLAN.md")
        self.assertEqual(self.run_check(root, 2, "small", "file:PLAN.md"), [])

    def _build_repo(self, ledger):
        root = self.make_repo({"README.md": "# p\n"})
        setup = commit(root, {"STAGES.md": STAGES_OPEN}, "setup")
        later = commit(root, {"BUILD-LEDGER.md": ledger, "app.py": "x = 1\n"}, "work")
        return root, setup, later

    def test_stage_3_only_the_setup_commit_fires(self):
        root, setup, _ = self._build_repo(LEDGER_OK)
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{setup},file:BUILD-LEDGER.md", setup), "after")

    def test_stage_3_without_any_commit_fires(self):
        root, setup, _ = self._build_repo(LEDGER_OK)
        self.assert_mentions(self.run_check(root, 3, "small", "file:BUILD-LEDGER.md", setup), "after")

    def test_stage_3_with_uncommitted_stages_file_fires(self):
        root, _, later = self._build_repo(LEDGER_OK)
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{later},file:BUILD-LEDGER.md", None), "after")

    def test_stage_3_second_cycle_setup_commit_alone_fires(self):
        root, _, _ = self._build_repo(LEDGER_OK)
        commit(root, remove=("STAGES.md",), message="archive the first cycle")
        second = commit(root, {"STAGES.md": STAGES_OPEN}, "second cycle setup")
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{second},file:BUILD-LEDGER.md", second), "after")

    def test_stage_3_ledger_without_review_rows_fires(self):
        root, setup, later = self._build_repo(LEDGER_NO_ROWS)
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{later},file:BUILD-LEDGER.md", setup), "review")

    def test_stage_3_ledger_without_reviews_section_fires(self):
        root, setup, later = self._build_repo("# Build ledger\n\n## Method\n\ntext\n")
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{later},file:BUILD-LEDGER.md", setup), "review")

    def test_stage_3_review_row_in_a_comment_does_not_count(self):
        root, setup, later = self._build_repo(
            "# L\n\n## Reviews\n\n<!--\n| Task | Reviewer | Result |\n|---|---|---|\n| 1 | a | b |\n-->\n")
        self.assert_mentions(self.run_check(root, 3, "small", f"commit:{later},file:BUILD-LEDGER.md", setup), "review")

    def test_stage_3_review_and_later_commit_passes(self):
        root, setup, later = self._build_repo(LEDGER_OK)
        self.assertEqual(self.run_check(root, 3, "small", f"commit:{later},file:BUILD-LEDGER.md", setup), [])

    def test_stage_4_full_needs_results(self):
        root = self.make_repo({"ARCHITECTURE.md": "arch\n", "RESULTS.md": "results\n"})
        self.assert_mentions(self.run_check(root, 4, "full", "file:ARCHITECTURE.md"), "RESULTS.md")
        self.assertEqual(self.run_check(root, 4, "full", "file:ARCHITECTURE.md,file:RESULTS.md"), [])

    def test_stage_4_small_needs_only_architecture(self):
        root = self.make_repo({"ARCHITECTURE.md": "arch\n"})
        self.assertEqual(self.run_check(root, 4, "small", "file:ARCHITECTURE.md"), [])

    def test_stage_5_and_6_need_ownership(self):
        root = self.make_repo({"OWNERSHIP.md": "answers\n"})
        for stage in (5, 6):
            with self.subTest(stage=stage):
                self.assert_mentions(self.run_check(root, stage, "small", "-"), "OWNERSHIP.md")
                self.assertEqual(self.run_check(root, stage, "small", "file:OWNERSHIP.md"), [])

    def test_stage_7_empty_retro_fires(self):
        root = self.make_repo({"AI-Agents.md": AI_EMPTY_RETRO})
        self.assert_mentions(self.run_check(root, 7, "small", "file:AI-Agents.md"), "Retro")

    def test_stage_7_missing_retro_fires(self):
        root = self.make_repo({"AI-Agents.md": "# AI log\n\n### 1. Title\n"})
        self.assert_mentions(self.run_check(root, 7, "small", "file:AI-Agents.md"), "Retro")

    def test_stage_7_filled_retro_passes(self):
        root = self.make_repo({"AI-Agents.md": AI_OK})
        self.assertEqual(self.run_check(root, 7, "small", "file:AI-Agents.md"), [])

    def test_rules_apply_only_at_their_stage(self):
        root = self.make_repo({"AI-Agents.md": "# AI log\n", "DECISIONS.md": DECISIONS_OK})
        self.assertEqual(self.run_check(root, 1, "small", "file:AI-Agents.md,file:DECISIONS.md"), [])


# ------------------------------------------------------------------- overrides

FIELD_VALUES = {"Date": "2026-11-09", "Stage": "3 Build", "What was skipped": "the second review",
                "Why": "the owner chose speed", "Risk accepted": "a defect may reach release",
                "How to close": "run the review", "Status": "open", "Closing evidence": "-",
                "Re-confirmed for release": "-"}


def entry(n, skip=(), **given):
    values = dict(FIELD_VALUES)
    for key, value in given.items():
        values[{"status": "Status", "closing": "Closing evidence", "reconfirmed": "Re-confirmed for release",
                "stage": "Stage", "date": "Date", "why": "Why"}[key]] = value
    lines = [f"### O{n}. Title {n}", ""]
    lines += [f"- **{label}:** {value}" for label, value in values.items() if label not in skip]
    return "\n".join(lines) + "\n"


def overrides_doc(*entries):
    return "# Overrides\n\n" + "\n".join(entries)


class OverrideRules(GitCase):
    def setUp(self):
        self.root = self.make_repo()

    def check(self, text, stages=None):
        return override_problems(text, self.root, stages or parse_stages(STAGES_OPEN))

    def test_valid_entry_passes(self):
        self.assertEqual(self.check(overrides_doc(entry(1))), [])

    def test_empty_file_passes(self):
        self.assertEqual(self.check("# Overrides\n"), [])

    def test_missing_field_is_named(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, skip=("Why",)))), "Why")

    def test_blank_field_is_named(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, why=""))), "Why")

    def test_placeholder_field_is_named(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, why="TBD"))), "Why")

    def test_numbering_gap_fires(self):
        self.assert_mentions(self.check(overrides_doc(entry(1), entry(3))), "numbering")

    def test_heading_without_the_exact_form_fires(self):
        text = overrides_doc(entry(1)).replace("### O1. Title 1", "### O1 Title 1")
        self.assert_mentions(self.check(text), "heading")

    def test_closed_without_closing_evidence_fires(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, status="closed", closing="-"))), "Closing evidence")

    def test_closed_with_closing_evidence_passes(self):
        self.assertEqual(self.check(overrides_doc(entry(1, status="closed", closing="commit abc1234"))), [])

    def test_unknown_status_fires(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, status="maybe"))), "Status")

    def test_bad_date_fires(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, date="yesterday"))), "Date")

    def test_bad_stage_fires(self):
        self.assert_mentions(self.check(overrides_doc(entry(1, stage="late"))), "Stage")

    def test_format_example_in_a_comment_is_not_an_entry(self):
        text = "# Overrides\n\n<!--\n" + entry(1) + "-->\n"
        self.assertEqual(parse_overrides(text), {})
        self.assertEqual(self.check(text), [])

    def test_removed_entry_has_vanished(self):
        commit(self.root, {"OVERRIDES.md": overrides_doc(entry(1), entry(2))}, "two overrides")
        self.assert_mentions(self.check(overrides_doc(entry(1))), "vanished")

    def test_deleted_file_has_vanished(self):
        commit(self.root, {"OVERRIDES.md": overrides_doc(entry(1))}, "an override")
        commit(self.root, remove=("OVERRIDES.md",), message="delete it")
        problems = override_problems(None, self.root, parse_stages(STAGES_OPEN))
        self.assert_mentions(problems, "vanished")

    def test_absent_file_without_history_is_fine(self):
        self.assertEqual(override_problems(None, self.root, parse_stages(STAGES_OPEN)), [])

    def test_open_entry_at_passed_stage_5_needs_reconfirmation(self):
        stages = parse_stages(table(row(5, "passed", "file:OWNERSHIP.md")))
        self.assert_mentions(self.check(overrides_doc(entry(1)), stages), "Re-confirmed")

    def test_open_entry_at_overridden_stage_5_needs_reconfirmation(self):
        stages = parse_stages(table(row(5, "overridden", "", "O1")))
        self.assert_mentions(self.check(overrides_doc(entry(1)), stages), "Re-confirmed")

    def test_reconfirmed_entry_at_stage_5_passes(self):
        stages = parse_stages(table(row(5, "passed", "file:OWNERSHIP.md")))
        self.assertEqual(self.check(overrides_doc(entry(1, reconfirmed="2026-11-10")), stages), [])

    def test_closed_entry_at_stage_5_needs_no_reconfirmation(self):
        stages = parse_stages(table(row(5, "passed", "file:OWNERSHIP.md")))
        self.assertEqual(self.check(overrides_doc(entry(1, status="closed", closing="commit abc1234")), stages), [])

    def test_open_entry_before_stage_5_needs_no_reconfirmation(self):
        stages = parse_stages(table(row(5, "open")))
        self.assertEqual(self.check(overrides_doc(entry(1)), stages), [])

    def test_parse_overrides_reads_status_stage_and_reconfirmation(self):
        parsed = parse_overrides(overrides_doc(entry(1, reconfirmed="2026-11-10"), entry(2, status="closed",
                                                                                         closing="x")))
        self.assertEqual(parsed["O1"], Override("open", "3 Build", "2026-11-10"))
        self.assertEqual(parsed["O2"].status, "closed")

    def test_crlf_and_bom_change_nothing(self):
        text = overrides_doc(entry(1, skip=("Why",)), entry(2))
        plain = self.check(text)
        self.assertTrue(plain)
        self.assertEqual(self.check("﻿" + text.replace("\n", "\r\n")), plain)
        self.assertEqual(parse_overrides("﻿" + text.replace("\n", "\r\n")), parse_overrides(text))


# ----------------------------------------------------------- stage table parser

class ParseRules(unittest.TestCase):
    def test_header_lines_and_rows_are_read(self):
        text = table(row(0, "passed", "file:a.md", "-"), extra=("Adopted-at: 2", "Traits: web, LLM"))
        stages = parse_stages(text)
        self.assertEqual((stages.size, stages.method, stages.adopted_at), ("small", "normal", 2))
        self.assertEqual(stages.traits, {"web", "llm"})
        self.assertEqual(sorted(stages.rows), list(range(8)))
        self.assertEqual(stages.rows[0], Row(line_of(text, "0 Intake"), "0 Intake", "passed", "file:a.md", "-"))

    def test_no_traits_line_is_none_and_traits_none_is_empty(self):
        self.assertIsNone(parse_stages(table()).traits)
        self.assertEqual(parse_stages(table(extra=("Traits: none",))).traits, set())

    def test_no_adopted_at_line_is_none(self):
        self.assertIsNone(parse_stages(table()).adopted_at)


# --------------------------------------------------------------------- command

def run_main(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class Command(GitCase):
    def project(self, stages=STAGES_OPEN, overrides=None, extra=None):
        files = {"STAGES.md": stages}
        if overrides is not None:
            files["OVERRIDES.md"] = overrides
        files.update(extra or {})
        return self.make_repo(files)

    def test_module_facts(self):
        self.assertEqual(check_gates.__version__, "0.2.0")
        self.assertEqual(len(STAGE_NAMES), 8)
        self.assertEqual(Problem("a", 3, "m").line, 3)
        for ext in (".py", ".ipynb", ".ps1", ".cs", ".sh"):
            self.assertIn(ext, SOURCE_EXTENSIONS)

    def test_tracked_files_handles_non_ascii_names(self):
        root = self.make_repo({"güncel.md": "x\n", "docs/a b.md": "y\n"})
        names = tracked_files(root)
        self.assertIn("güncel.md", names)
        self.assertIn("docs/a b.md", names)

    def test_clean_project_exits_0(self):
        root = self.project()
        code, out, _ = run_main([str(root)])
        self.assertEqual((code, out), (0, ""))

    def test_problems_go_to_stdout_and_exit_1(self):
        root = self.project(stages=table(row(0, "passed")))
        code, out, _ = run_main([str(root)])
        self.assertEqual(code, 1)
        self.assertRegex(out, r"^STAGES\.md:\d+: ")

    def test_missing_stages_file_is_a_problem(self):
        root = self.make_repo()
        problems, _ = check_project(root)
        self.assertEqual([(p.file, p.line) for p in problems], [("STAGES.md", 0)])

    def test_open_override_is_a_note_and_not_a_failure(self):
        root = self.project(overrides=overrides_doc(entry(1)))
        problems, notes = check_project(root)
        self.assertEqual(problems, [])
        self.assertTrue(any("O1" in n for n in notes))
        code, out, err = run_main([str(root)])
        self.assertEqual((code, out), (0, ""))
        self.assertIn("O1", err)

    def test_closed_override_is_not_listed(self):
        root = self.project(overrides=overrides_doc(entry(1, status="closed", closing="commit abc1234")))
        self.assertEqual(check_project(root), ([], []))

    def test_invalid_utf8_is_a_problem_at_its_line(self):
        root = self.project(stages=b"Size: small\n\xff\n")
        problems, _ = check_project(root)
        self.assertEqual(len(problems), 1)
        self.assertEqual((problems[0].file, problems[0].line), ("STAGES.md", 2))
        self.assertIn("UTF-8", problems[0].message)

    def test_invalid_utf8_in_overrides_is_a_problem_not_a_crash(self):
        root = self.project(overrides=b"# Overrides\n\xff\n")
        problems, _ = check_project(root)
        self.assertEqual([(p.file, p.line) for p in problems], [("OVERRIDES.md", 2)])

    def test_not_a_git_repository_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = run_main([tmp])
        self.assertEqual(code, 2)
        self.assertIn("git", err)

    def test_not_a_directory_exits_2(self):
        self.assertEqual(run_main([str(ROOT / "nope-folder")])[0], 2)

    def test_two_arguments_exit_2(self):
        self.assertEqual(run_main(["a", "b"])[0], 2)

    def test_subfolder_of_a_repository_exits_2(self):
        root = self.project(extra={"sub/x.txt": "x\n"})
        code, _, err = run_main([str(root / "sub")])
        self.assertEqual(code, 2)
        self.assertIn("top", err)

    def test_shallow_clone_exits_2(self):
        root = self.make_repo()
        commit(root, {"a.txt": "a\n"}, "second")
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone"
            subprocess.run(["git", "clone", "-q", "--depth", "1", root.as_uri(), str(clone)],
                           check=True, capture_output=True, env=GIT_ENV)
            code, _, err = run_main([str(clone)])
        self.assertEqual(code, 2)
        self.assertIn("shallow", err)

    def test_trust_limit_is_printed_on_every_run(self):
        self.assertIn("git identity", TRUST_LIMIT)
        root = self.project()
        for args in ([str(root)], ["a", "b"]):
            with self.subTest(args=len(args)):
                self.assertIn(TRUST_LIMIT, run_main(args)[2])

    def test_default_folder_is_the_current_directory(self):
        root = self.project()
        old = os.getcwd()
        os.chdir(root)
        try:
            code, _, _ = run_main([])
        finally:
            os.chdir(old)
        self.assertEqual(code, 0)

    def test_run_as_a_script_exits_with_the_code(self):
        root = self.project()
        script = ROOT / "skills" / "agentic-principles" / "scripts" / "check_gates.py"
        result = subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("git identity", result.stderr)


class ShippedTemplates(unittest.TestCase):
    def read(self, name):
        return (ROOT / "templates" / name).read_text(encoding="utf-8-sig")

    def test_stages_template_has_eight_open_stages(self):
        stages = parse_stages(self.read("STAGES.md"))
        self.assertEqual(stages.errors, [])
        self.assertEqual({r.status for r in stages.rows.values()}, {"open"})
        self.assertEqual(len(stages.rows), 8)

    def test_overrides_template_has_no_phantom_entry(self):
        text = self.read("OVERRIDES.md")
        self.assertEqual(parse_overrides(text), {})
        self.assertIn("### O1.", text)            # the format is shown, inside a comment
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(override_problems(text, tmp, parse_stages(self.read("STAGES.md"))), [])


if __name__ == "__main__":
    unittest.main()
