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
    attack_problems,
    attack_rungs,
    check_project,
    components,
    dependency_problems,
    evidence_content_problems,
    file_map_problems,
    main,
    manifest_dependencies,
    override_problems,
    parse_overrides,
    parse_stages,
    requirement_ids,
    section_override,
    stage_problems,
    tracked_files,
)
from check_gates import test_table_problems as tt_problems  # noqa: E402  (not a test: a check function)

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

    def test_override_naming_a_stage_beyond_7_is_a_problem_not_a_crash(self):
        for bad in ("8 Foo", "9 Foo", "99"):
            with self.subTest(stage=bad):
                problems = self.check(table(row(0, "overridden", "", "O1")), {"O1": Override("open", bad, "-")})
                self.assert_mentions(problems, "stage")

    def test_non_utf8_evidence_file_is_a_problem_at_its_line(self):
        commit(self.root, {"REQUIREMENTS.md": b"REQ-1 ok\n\xff\n"})
        problems = self.check(self.stage0("file:REQUIREMENTS.md,file:ATTACKS.md"))
        hit = [p for p in problems if "UTF-8" in p.message]
        self.assertEqual([(p.file, p.line) for p in hit], [("REQUIREMENTS.md", 2)])

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


# ------------------------------------------------------ architecture and attacks

E = "tests/test_a.py"
BOM = "﻿"
COMP_COLS = ["Component", "What it does"]
MAP_COLS = ["Path", "What it does"]
TEST_COLS = ["Part", "1 Written first", "2 Catches breakage", "3 Input range", "4 Real integration",
             "5 Deliberate failure"]
DEP_COLS = ["Name", "Version", "Why it is here", "What breaks without it"]
ATK_COLS = ["ID", "Attack", "Rung", "Drafted by"]


def md_table(columns, rows):
    def line(cells):
        return "| " + " | ".join(cells) + " |"
    return "\n".join([line(columns), line(["---"] * len(columns))] + [line(r) for r in rows]) + "\n"


def dep_row(spec):
    if not isinstance(spec, str):
        return spec
    parts = spec.split()
    return (parts[0], parts[1] if len(parts) > 1 else "1.0", "needed", "stops working")


def doc(map=None, deps=None, tests=None, comps=None, override=None, manual=None):
    """An ARCHITECTURE.md with only the sections asked for. `override` goes into every section given."""
    def section(heading, body):
        top = f"Override: {override}\n\n" if override else ""
        return f"## {heading}\n\n{top}{body}"
    out = ["# Architecture\n", "## Diagram\n\nA to B\n"]
    if comps is not None:
        out.append("## Components\n\n" + md_table(COMP_COLS, [(c, "does work") for c in comps]))
    if map is not None:
        out.append(section("File map", md_table(MAP_COLS, [(m, "a file") if isinstance(m, str) else m
                                                            for m in map])))
    if deps is not None:
        note = f"Manifests: manual: {manual}\n\n" if manual else ""
        out.append(section("Dependencies", note + md_table(DEP_COLS, [dep_row(d) for d in deps])))
    if tests is not None:
        out.append(section("Tests", md_table(TEST_COLS, tests)))
    return "\n".join(out)


def trow(part, *rungs):
    return (part, *rungs)


def attack_doc(count, rung="3", size_rows=None):
    rows = size_rows or [(f"ATK-{i}", "feed it garbage", rung, "fresh session") for i in range(1, count + 1)]
    return "# Attacks\n\n" + md_table(ATK_COLS, rows)


def ov(status, stage):
    return Override(status, stage, "-")


ELEVEN = [f"src/f{i}.py" for i in range(11)]


class ArchitectureRules(GitCase):
    def setUp(self):
        self.root = self.make_repo({E: "x = 1\n", "README.md": "# p\n"})
        self.sha = git(self.root, "rev-parse", "HEAD")

    # ---- file map
    def fm(self, text, tracked, overrides=None):
        return file_map_problems(text, tracked, overrides or {})

    def test_file_not_in_the_map_is_named(self):
        self.assert_mentions(self.fm(doc(map=["src/a.py"]), ["src/a.py", "src/b.py"]), "src/b.py")

    def test_folder_row_covers_everything_below(self):
        self.assertEqual(self.fm(doc(map=["src/"]), ["src/a.py", "src/b.py"]), [])

    def test_folder_with_eleven_files_fires_and_names_the_limit(self):
        self.assert_mentions(self.fm(doc(map=["src/"]), ELEVEN), "10")

    def test_folder_with_ten_files_passes(self):
        self.assertEqual(self.fm(doc(map=["src/"]), ELEVEN[:10]), [])

    def test_bulk_reason_lifts_the_limit(self):
        text = doc(map=[("src/", "audio samples (bulk: recordings)")])
        self.assertEqual(self.fm(text, ELEVEN), [])

    def test_bulk_without_a_reason_does_not_lift_it(self):
        self.assert_mentions(self.fm(doc(map=[("src/", "samples (bulk: )")]), ELEVEN), "10")

    def test_slash_alone_is_refused(self):
        self.assert_mentions(self.fm(doc(map=["/"]), ["a.py"]), "refused")

    def test_slash_alone_is_refused_even_with_a_bulk_reason(self):
        problems = self.fm(doc(map=[("/", "everything (bulk: all)"), "a.py"]), ["a.py"])
        self.assertEqual(len(problems), 1)

    def test_row_for_a_missing_file_is_named(self):
        self.assert_mentions(self.fm(doc(map=["gone.py"]), []), "gone.py")

    def test_folder_row_matching_nothing_is_named(self):
        self.assert_mentions(self.fm(doc(map=["nowhere/"]), []), "nowhere/")

    def test_backslash_path_with_a_space_matches(self):
        self.assertEqual(self.fm(doc(map=["src\\my file.py"]), ["src/my file.py"]), [])

    def test_folder_prefix_is_not_a_substring_match(self):
        self.assert_mentions(self.fm(doc(map=["src/"]), ["src/a.py", "srcother/b.py"]), "srcother/b.py")

    def test_blank_description_is_named(self):
        self.assert_mentions(self.fm(doc(map=[("a.py", "")]), ["a.py"]), "description")

    def test_override_for_this_stage_silences_the_map(self):
        text = doc(map=[], override="O1")
        self.assertEqual(self.fm(text, ["a.py"], {"O1": ov("open", "5 Ship")}), [])

    def test_override_for_another_stage_does_not_silence(self):
        text = doc(map=[], override="O1")
        self.assertTrue(self.fm(text, ["a.py"], {"O1": ov("open", "0 Intake")}))

    def test_closed_override_does_not_silence(self):
        text = doc(map=[], override="O1")
        self.assertTrue(self.fm(text, ["a.py"], {"O1": ov("closed", "5 Ship")}))

    def test_unknown_override_is_named(self):
        self.assert_mentions(self.fm(doc(map=[], override="O9"), ["a.py"]), "O9")

    def test_missing_section_is_a_problem(self):
        self.assert_mentions(self.fm(doc(deps=[]), ["a.py"]), "File map")

    def test_file_map_wrong_columns_are_a_problem(self):
        text = "## File map\n\n| File | Purpose |\n|---|---|\n| a.py | x |\n"
        self.assert_mentions(self.fm(text, ["a.py"]), "columns")

    def test_map_rows_inside_a_comment_do_not_count(self):
        text = "## File map\n\n<!--\n" + md_table(MAP_COLS, [("a.py", "x")]) + "-->\n"
        self.assertTrue(self.fm(text, ["a.py"]))

    def test_crlf_and_bom_change_nothing(self):
        text = doc(map=["src/a.py"])
        plain = self.fm(text, ["src/a.py", "src/b.py"])
        self.assertTrue(plain)
        self.assertEqual(self.fm(BOM + text.replace("\n", "\r\n"), ["src/a.py", "src/b.py"]), plain)

    # ---- dependencies
    def dp(self, text, deps, unreadable=(), overrides=None):
        return dependency_problems(text, deps, list(unreadable), overrides or {})

    def test_manifest_dependency_missing_from_the_table_is_named(self):
        self.assert_mentions(self.dp(doc(deps=["httpx"]), {"httpx": None, "rich": None}), "rich")

    def test_table_dependency_missing_from_the_manifests_is_named(self):
        self.assert_mentions(self.dp(doc(deps=["httpx"]), {}), "httpx")

    def test_matching_table_and_manifest_pass(self):
        self.assertEqual(self.dp(doc(deps=["httpx 1.0"]), {"httpx": "1.0"}), [])

    def test_wrong_version_is_named(self):
        self.assert_mentions(self.dp(doc(deps=["httpx 2.0"]), {"httpx": "1.0"}), "version")

    def test_unpinned_manifest_entry_accepts_any_version(self):
        self.assertEqual(self.dp(doc(deps=["httpx 2.0"]), {"httpx": None}), [])

    def test_blank_why_is_named(self):
        text = doc(deps=[("httpx", "1.0", "", "x")])
        self.assert_mentions(self.dp(text, {"httpx": "1.0"}), "Why")

    def test_blank_breaks_cell_is_named(self):
        text = doc(deps=[("httpx", "1.0", "x", "")])
        self.assert_mentions(self.dp(text, {"httpx": "1.0"}), "What breaks")

    def test_name_spelling_is_normalised(self):
        self.assertEqual(self.dp(doc(deps=["Foo_Bar"]), {"foo-bar": None}), [])

    def test_unreadable_manifest_is_named(self):
        self.assert_mentions(self.dp(doc(deps=[]), {}, ["go.mod"]), "go.mod")

    def test_manual_line_with_a_reason_accepts_unreadable_manifests(self):
        self.assertEqual(self.dp(doc(deps=[], manual="no parser"), {}, ["go.mod"]), [])

    def test_manual_line_takes_the_table_as_stated(self):
        self.assertEqual(self.dp(doc(deps=["httpx"], manual="no parser"), {"rich": None}, ["go.mod"]), [])

    def test_manual_line_without_a_reason_fires(self):
        text = doc(deps=[]).replace("## Dependencies\n\n", "## Dependencies\n\nManifests: manual:\n\n")
        self.assert_mentions(self.dp(text, {}, ["go.mod"]), "reason")

    def test_empty_table_with_no_manifests_passes(self):
        self.assertEqual(self.dp(doc(deps=[]), {}), [])

    def test_dependency_override_for_this_stage_silences(self):
        text = doc(deps=[], override="O1")
        self.assertEqual(self.dp(text, {"rich": None}, ["go.mod"], {"O1": ov("open", "5 Ship")}), [])

    def test_dependency_override_for_another_stage_does_not_silence(self):
        text = doc(deps=[], override="O1")
        self.assertTrue(self.dp(text, {"rich": None}, [], {"O1": ov("open", "4 Verify")}))

    def test_missing_dependencies_section_is_a_problem(self):
        self.assert_mentions(self.dp(doc(map=[]), {}), "Dependencies")

    # ---- test table
    def ttp(self, rows, size, parts, rungs=None, overrides=None, text=None):
        text = doc(tests=rows) if text is None else text
        return tt_problems(text, size, parts, rungs or {}, ls(self.root), self.root, overrides or {})

    def test_no_rows_fires(self):
        self.assert_mentions(self.ttp([], "full", set()), "no rows")

    def test_blank_required_rung_names_the_rung(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, "", E, E, E)], "full", {"REQ-1"}), "rung 2")

    def test_prose_in_a_rung_cell_is_refused(self):
        problems = self.ttp([trow("REQ-1", E, "looks fine to me", E, E, E)], "full", {"REQ-1"})
        self.assert_mentions(problems, "no tracked file or commit")

    def test_na_without_a_reason_is_refused(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, "n/a", E, E, E)], "full", {"REQ-1"}), "reason")

    def test_na_with_an_empty_reason_is_refused(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, "n/a:  ", E, E, E)], "full", {"REQ-1"}), "reason")

    def test_na_with_a_placeholder_reason_is_refused(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, "n/a: tbd", E, E, E)], "full", {"REQ-1"}), "reason")

    def test_row_is_not_matched_by_a_longer_id(self):
        problems = self.ttp([trow("ATK-1", E, E, E, E, E)], "full", {"ATK-10"})
        self.assert_mentions(problems, "'ATK-1' is not a part")
        self.assert_mentions(problems, "ATK-10 has no row")

    def test_na_with_a_reason_passes(self):
        rows = [trow("REQ-1", E, "n/a: pure text only", E, E, E)]
        self.assertEqual(self.ttp(rows, "full", {"REQ-1"}), [])

    def test_untracked_file_is_refused(self):
        write(self.root, "loose_test.py", "x\n")
        rows = [trow("REQ-1", "loose_test.py", E, E, E, E)]
        self.assert_mentions(self.ttp(rows, "full", {"REQ-1"}), "rung 1")

    def test_test_id_after_the_path_is_accepted(self):
        rows = [trow("REQ-1", f"{E}::TestA::test_x", f"`{E}`", E, E, E)]
        self.assertEqual(self.ttp(rows, "full", {"REQ-1"}), [])

    def test_commit_on_the_history_is_accepted(self):
        rows = [trow("REQ-1", self.sha, self.sha[:8], E, E, E)]
        self.assertEqual(self.ttp(rows, "full", {"REQ-1"}), [])

    def test_unknown_commit_is_refused(self):
        rows = [trow("REQ-1", "a" * 40, E, E, E, E)]
        self.assert_mentions(self.ttp(rows, "full", {"REQ-1"}), "rung 1")

    def test_commit_on_another_branch_is_refused(self):
        branch = git(self.root, "rev-parse", "--abbrev-ref", "HEAD")
        git(self.root, "checkout", "-q", "-b", "side")
        other = commit(self.root, {"side.txt": "x\n"}, "side work")
        git(self.root, "checkout", "-q", branch)
        rows = [trow("REQ-1", other, E, E, E, E)]
        self.assert_mentions(self.ttp(rows, "full", {"REQ-1"}), "rung 1")

    def test_full_needs_every_rung(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, E, "", E, E)], "full", {"REQ-1"}), "rung 3")

    def test_small_needs_only_rungs_1_and_2(self):
        self.assertEqual(self.ttp([trow("REQ-1", E, E, "", "", "")], "small", {"REQ-1"}), [])

    def test_small_still_needs_rung_2(self):
        self.assert_mentions(self.ttp([trow("REQ-1", E, "", "", "", "")], "small", {"REQ-1"}), "rung 2")

    def test_whole_system_row_leaves_the_real_parts_unlisted(self):
        problems = self.ttp([trow("Whole system", E, E, E, E, E)], "full", {"REQ-1", "ATK-1"})
        self.assert_mentions(problems, "REQ-1 has no row")
        self.assert_mentions(problems, "ATK-1 has no row")
        self.assert_mentions(problems, "Whole system")

    def test_two_ids_in_one_row_are_refused(self):
        problems = self.ttp([trow("REQ-1, ATK-1", E, E, E, E, E)], "full", {"REQ-1", "ATK-1"})
        self.assert_mentions(problems, "one part per row")
        self.assert_mentions(problems, "REQ-1 has no row")

    def test_id_is_compared_exactly(self):
        problems = self.ttp([trow("ATK-10", E, E, E, E, E)], "full", {"ATK-1"})
        self.assert_mentions(problems, "ATK-1 has no row")
        self.assert_mentions(problems, "ATK-10")

    def test_component_row_is_matched_exactly(self):
        rows = [trow("Parser", E, E, E, E, E)]
        self.assertEqual(self.ttp(rows, "full", {"Parser"}), [])
        self.assert_mentions(self.ttp(rows, "full", {"Parser", "Store"}), "Store has no row")

    def test_a_part_with_two_rows_is_named(self):
        rows = [trow("REQ-1", E, E, E, E, E), trow("REQ-1", E, E, E, E, E)]
        self.assert_mentions(self.ttp(rows, "full", {"REQ-1"}), "more than one row")

    def test_attack_rung_is_required_on_small(self):
        rows = [trow("ATK-1", E, E, "", "", "")]
        self.assert_mentions(self.ttp(rows, "small", {"ATK-1"}, {"ATK-1": 5}), "rung 5")

    def test_attack_rung_filled_passes_on_small(self):
        rows = [trow("ATK-1", E, E, "", "", E)]
        self.assertEqual(self.ttp(rows, "small", {"ATK-1"}, {"ATK-1": 5}), [])

    def test_attack_rung_applies_only_to_its_attack(self):
        rows = [trow("REQ-1", E, E, "", "", "")]
        self.assertEqual(self.ttp(rows, "small", {"REQ-1", }, {"ATK-1": 5}), [])

    def test_wrong_columns_are_a_problem(self):
        text = "## Tests\n\n| Part | Evidence |\n|---|---|\n| REQ-1 | x |\n"
        self.assert_mentions(self.ttp(None, "small", {"REQ-1"}, text=text), "columns")

    def test_missing_tests_section_is_a_problem(self):
        self.assert_mentions(self.ttp(None, "small", set(), text=doc(map=[])), "Tests")

    def test_tests_override_binds_at_stage_4(self):
        text = doc(tests=[], override="O1")
        self.assertEqual(self.ttp(None, "full", {"REQ-1"}, overrides={"O1": ov("open", "4 Verify")}, text=text), [])
        self.assertTrue(self.ttp(None, "full", {"REQ-1"}, overrides={"O1": ov("open", "5 Ship")}, text=text))

    # ---- readers
    def test_components_are_read_from_the_table(self):
        self.assertEqual(components(doc(comps=["Parser", "Store"])), {"Parser", "Store"})

    def test_components_without_the_section_are_empty(self):
        self.assertEqual(components(doc(map=[])), set())

    def test_requirement_ids_ignore_comments_and_longer_words(self):
        text = "| REQ-1 | a |\n| REQ-12 | b |\n<!-- REQ-3 -->\nXREQ-4\n"
        self.assertEqual(requirement_ids(text), {"REQ-1", "REQ-12"})

    def test_section_override_requires_an_open_override_for_the_stage(self):
        text = "Override: O1\n"
        self.assertTrue(section_override(text, {"O1": ov("open", "5 Ship")}, "5"))
        self.assertFalse(section_override(text, {"O1": ov("closed", "5 Ship")}, "5"))
        self.assertFalse(section_override(text, {"O1": ov("open", "4 Verify")}, "5"))
        self.assertFalse(section_override(text, {}, "5"))
        self.assertFalse(section_override("no override here\n", {"O1": ov("open", "5 Ship")}, "5"))

    def test_section_override_does_not_read_a_stage_beyond_7(self):
        self.assertFalse(section_override("Override: O1\n", {"O1": ov("open", "99")}, "5"))


class AttackRules(unittest.TestCase):
    def test_enough_rows_pass(self):
        self.assertEqual(attack_problems(attack_doc(3), "small"), [])
        self.assertEqual(attack_problems(attack_doc(5), "full"), [])

    def test_two_rows_on_small_fire(self):
        self.assertTrue(any("3" in m for m in messages(attack_problems(attack_doc(2), "small"))))

    def test_four_rows_on_full_fire(self):
        self.assertTrue(any("5" in m for m in messages(attack_problems(attack_doc(4), "full"))))

    def test_example_marker_fires_at_its_line(self):
        text = attack_doc(3).replace("ATK-2 | feed it garbage", "ATK-2 | feed it garbage (EXAMPLE)")
        problems = attack_problems(text, "small")
        hit = [p for p in problems if "(EXAMPLE)" in p.message]
        self.assertEqual([p.line for p in hit], [line_of(text, "ATK-2")])

    def test_example_marker_in_a_comment_is_ignored(self):
        text = "<!-- rows marked (EXAMPLE) are samples -->\n" + attack_doc(3)
        self.assertEqual(attack_problems(text, "small"), [])

    def test_rung_must_be_3_5_or_dash(self):
        self.assertEqual(attack_problems(attack_doc(3, rung="-"), "small"), [])
        self.assertTrue(attack_problems(attack_doc(3, rung="4"), "small"))
        self.assertTrue(attack_problems(attack_doc(3, rung=""), "small"))

    def test_ids_must_run_in_order(self):
        rows = [("ATK-1", "a", "3", "x"), ("ATK-3", "b", "3", "x"), ("ATK-4", "c", "3", "x")]
        self.assertTrue(any("ATK-2" in m for m in messages(attack_problems(attack_doc(0, size_rows=rows), "small"))))

    def test_blank_attack_and_blank_author_fire(self):
        rows = [("ATK-1", "", "3", "x"), ("ATK-2", "b", "3", ""), ("ATK-3", "c", "3", "x")]
        problems = messages(attack_problems(attack_doc(0, size_rows=rows), "small"))
        self.assertTrue(any("Attack" in m for m in problems))
        self.assertTrue(any("Drafted by" in m for m in problems))

    def test_wrong_columns_fire(self):
        self.assertTrue(attack_problems("| ID | Idea |\n|---|---|\n| ATK-1 | x |\n", "small"))

    def test_no_table_fires(self):
        self.assertTrue(attack_problems("- ATK-1 feed it garbage\n", "small"))

    def test_crlf_and_bom_change_nothing(self):
        text = attack_doc(2)
        plain = attack_problems(text, "small")
        self.assertTrue(plain)
        self.assertEqual(attack_problems(BOM + text.replace("\n", "\r\n"), "small"), plain)

    def test_rungs_are_read_per_attack(self):
        rows = [("ATK-1", "a", "3", "x"), ("ATK-2", "b", "5", "x"), ("ATK-3", "c", "-", "x")]
        self.assertEqual(attack_rungs(attack_doc(0, size_rows=rows)), {"ATK-1": 3, "ATK-2": 5})


class ManifestRules(unittest.TestCase):
    def tmp_with(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, content in files.items():
            write(tmp.name, name, content)
        return Path(tmp.name)

    def read(self, files):
        return manifest_dependencies(self.tmp_with(files), list(files))

    def test_requirements_names_are_normalised_and_options_skipped(self):
        self.assertEqual(self.read({"requirements.txt": "Foo_Bar==1.2\n# note\n-r other.txt\n"}),
                         ({"foo-bar": "1.2"}, []))

    def test_requirements_unpinned_extras_and_markers(self):
        text = "requests>=2.0\nrich[extra]==13.0 ; python_version > '3.8'\nflask  # web\n.\ngit+https://example.com/x.git\n"
        deps, unreadable = self.read({"requirements-dev.txt": text})
        self.assertEqual(deps, {"requests": None, "rich": "13.0", "flask": None})
        self.assertEqual(unreadable, [])

    def test_requirements_with_a_bom_and_crlf(self):
        deps, _ = self.read({"requirements.txt": BOM + "httpx==0.1\r\nrich==1.0\r\n"})
        self.assertEqual(deps, {"httpx": "0.1", "rich": "1.0"})

    def test_requirements_that_is_not_utf8_is_unreadable(self):
        self.assertEqual(self.read({"requirements.txt": b"httpx==1\n\xff\n"}), ({}, ["requirements.txt"]))

    def test_poetry_pyproject_is_unreadable(self):
        text = "[tool.poetry]\nname = 'x'\n[tool.poetry.dependencies]\nrequests = '^2'\n"
        self.assertEqual(self.read({"pyproject.toml": text}), ({}, ["pyproject.toml"]))

    def test_dependency_groups_pyproject_is_unreadable(self):
        text = "[project]\nname = 'x'\ndependencies = ['requests']\n[dependency-groups]\ndev = ['pytest']\n"
        self.assertEqual(self.read({"pyproject.toml": text}), ({}, ["pyproject.toml"]))

    def test_broken_pyproject_is_unreadable_not_a_crash(self):
        self.assertEqual(self.read({"pyproject.toml": "[project\n"}), ({}, ["pyproject.toml"]))

    def test_standard_pyproject_reads_dependencies_and_optional_ones(self):
        text = ("[project]\nname = 'x'\ndependencies = ['requests==2.1', 'Rich>=1']\n"
                "[project.optional-dependencies]\ntest = ['pytest-cov==4.0']\n")
        deps, unreadable = self.read({"pyproject.toml": text})
        self.assertEqual(deps, {"requests": "2.1", "rich": None, "pytest-cov": "4.0"})
        self.assertEqual(unreadable, [])

    def test_nested_package_json_reads_both_sections(self):
        text = '{"dependencies": {"left-pad": "1.3.0", "react": "^18.0.0"}, "devDependencies": {"jest": "29.0.0"}}'
        deps, unreadable = self.read({"web/package.json": text})
        self.assertEqual(deps, {"left-pad": "1.3.0", "react": None, "jest": "29.0.0"})
        self.assertEqual(unreadable, [])

    def test_package_json_inside_node_modules_is_ignored(self):
        text = '{"dependencies": {"left-pad": "1.3.0"}}'
        self.assertEqual(self.read({"node_modules/x/package.json": text}), ({}, []))

    def test_broken_package_json_is_unreadable(self):
        self.assertEqual(self.read({"package.json": "{not json"}), ({}, ["package.json"]))

    def test_unsupported_manifests_are_listed_not_skipped(self):
        names = ["go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "composer.json",
                 "environment.yml", "setup.py", "Pipfile"]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.read({name: "x\n"}), ({}, [name]))

    def test_tracked_file_missing_from_the_folder_is_unreadable(self):
        root = self.tmp_with({"README.md": "x\n"})
        self.assertEqual(manifest_dependencies(root, ["requirements.txt"]), ({}, ["requirements.txt"]))

    def test_other_files_are_not_manifests(self):
        self.assertEqual(self.read({"notes.txt": "requests\n", "src/app.py": "x\n"}), ({}, []))


class Timing(GitCase):
    def repo(self, stages, extra=None):
        files = {"STAGES.md": stages, "README.md": "# p\n"}
        files.update(extra or {})
        return self.make_repo(files)

    def only(self, root, name):
        return [p for p in check_project(root)[0] if p.file == name]

    def valid_files(self, **sections):
        """Tracked files for a project whose ARCHITECTURE.md is consistent with them."""
        names = ["README.md", "STAGES.md", "ARCHITECTURE.md", "REQUIREMENTS.md", "ATTACKS.md", E]
        given = dict(comps=["Parser"], map=names, deps=[],
                     tests=[trow("Parser", E, E, "", "", ""), trow("REQ-1", E, E, "", "", ""),
                            trow("ATK-1", E, E, E, "", ""), trow("ATK-2", E, E, "", "", ""),
                            trow("ATK-3", E, E, "", "", "")])
        given.update(sections)
        attacks = attack_doc(0, size_rows=[("ATK-1", "a", "3", "x"), ("ATK-2", "b", "-", "x"),
                                           ("ATK-3", "c", "-", "x")])
        return {"ARCHITECTURE.md": doc(**given), "REQUIREMENTS.md": REQ_OK, "ATTACKS.md": attacks,
                E: "x = 1\n"}

    def both(self):
        return table(row(4, "passed", "file:ARCHITECTURE.md"), row(5, "passed", "file:OWNERSHIP.md"))

    def test_stage_4_open_does_not_need_the_architecture_file(self):
        self.assertEqual(self.only(self.repo(table()), "ARCHITECTURE.md"), [])

    def test_stage_5_passed_without_the_file_reports_it_missing(self):
        problems = self.only(self.repo(table(row(5, "passed", "file:OWNERSHIP.md"))), "ARCHITECTURE.md")
        self.assertEqual([p.line for p in problems], [0])
        self.assert_mentions(problems, "missing")

    def test_consistent_architecture_passes_at_stages_4_and_5(self):
        root = self.repo(self.both(), self.valid_files())
        self.assertEqual(self.only(root, "ARCHITECTURE.md"), [])

    def test_test_table_binds_at_stage_4_not_before(self):
        extra = {"ARCHITECTURE.md": doc(comps=[], map=[], deps=[], tests=[])}
        open_root = self.repo(table(), extra)
        self.assertEqual(self.only(open_root, "ARCHITECTURE.md"), [])
        passed_root = self.repo(table(row(4, "passed", "file:ARCHITECTURE.md")), extra)
        problems = self.only(passed_root, "ARCHITECTURE.md")
        self.assert_mentions(problems, "no rows")
        self.assertFalse(any("map" in m.lower() for m in messages(problems)), problems)

    def test_file_map_and_dependencies_bind_at_stage_5_not_before(self):
        extra = {"ARCHITECTURE.md": doc(comps=[], map=[], deps=[], tests=[trow("x", E, E, E, E, E)]),
                 "requirements.txt": "rich==1.0\n"}
        stage4 = self.repo(table(row(4, "passed", "file:ARCHITECTURE.md")), extra)
        self.assertFalse(any("rich" in m or "map" in m.lower() for m in messages(self.only(stage4, "ARCHITECTURE.md"))))
        stage5 = self.repo(table(row(5, "passed", "file:OWNERSHIP.md")), extra)
        problems = messages(self.only(stage5, "ARCHITECTURE.md"))
        self.assertTrue(any("README.md" in m for m in problems), problems)
        self.assertTrue(any("rich" in m for m in problems), problems)

    def test_test_table_needs_a_row_for_each_requirement_from_requirements_md(self):
        files = self.valid_files(tests=[trow("Parser", E, E, "", "", ""), trow("ATK-1", E, E, E, "", ""),
                                        trow("ATK-2", E, E, "", "", ""), trow("ATK-3", E, E, "", "", "")])
        root = self.repo(table(row(4, "passed", "file:ARCHITECTURE.md")), files)
        self.assert_mentions(self.only(root, "ARCHITECTURE.md"), "REQ-1 has no row")

    def test_attack_rung_from_attacks_md_is_required(self):
        files = self.valid_files(tests=[trow("Parser", E, E, "", "", ""), trow("REQ-1", E, E, "", "", ""),
                                        trow("ATK-1", E, E, "", "", ""), trow("ATK-2", E, E, "", "", ""),
                                        trow("ATK-3", E, E, "", "", "")])
        root = self.repo(table(row(4, "passed", "file:ARCHITECTURE.md")), files)
        self.assert_mentions(self.only(root, "ARCHITECTURE.md"), "ATK-1: rung 3")

    def test_override_in_a_section_silences_it_through_check_project(self):
        extra = {"ARCHITECTURE.md": doc(comps=[], map=[], deps=[], override="O1"),
                 "OVERRIDES.md": overrides_doc(entry(1, stage="5 Ship"))}
        root = self.repo(table(row(5, "passed", "file:OWNERSHIP.md")), extra)
        self.assertEqual(self.only(root, "ARCHITECTURE.md"), [])
        extra.pop("OVERRIDES.md")
        root = self.repo(table(row(5, "passed", "file:OWNERSHIP.md")), extra)
        self.assert_mentions(self.only(root, "ARCHITECTURE.md"), "O1")

    def test_attack_list_binds_at_stage_0(self):
        extra = {"ATTACKS.md": attack_doc(2)}
        self.assertEqual(self.only(self.repo(table(), extra), "ATTACKS.md"), [])
        passed = self.repo(table(row(0, "passed", "file:REQUIREMENTS.md,file:ATTACKS.md")),
                           dict(extra, **{"REQUIREMENTS.md": REQ_OK}))
        self.assert_mentions(self.only(passed, "ATTACKS.md"), "3")

    def test_enough_attacks_pass_at_stage_0(self):
        root = self.repo(table(row(0, "passed", "file:REQUIREMENTS.md,file:ATTACKS.md")),
                         {"ATTACKS.md": attack_doc(3), "REQUIREMENTS.md": REQ_OK})
        self.assertEqual(self.only(root, "ATTACKS.md"), [])

    def test_non_utf8_architecture_is_one_problem_at_its_line_not_a_crash(self):
        root = self.repo(self.both(), {"ARCHITECTURE.md": b"# Architecture\n\xff\n"})
        problems = self.only(root, "ARCHITECTURE.md")
        self.assertEqual([(p.line, "UTF-8" in p.message) for p in problems], [(2, True)])

    def test_non_utf8_attacks_is_reported_once(self):
        root = self.repo(table(row(0, "passed", "file:REQUIREMENTS.md,file:ATTACKS.md")),
                         {"ATTACKS.md": b"| ID |\n\xff\n", "REQUIREMENTS.md": REQ_OK})
        self.assertEqual(len([p for p in self.only(root, "ATTACKS.md") if "UTF-8" in p.message]), 1)


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
