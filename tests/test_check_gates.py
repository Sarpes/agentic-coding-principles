"""Tests for the stage gate (check_gates.py). Real temporary git repositories are built where history matters."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
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
    cycle_start,
    components,
    dependency_problems,
    detect_traits,
    evidence_content_problems,
    explain_back_problems,
    file_map_problems,
    go_live_problems,
    grilling_problems,
    main,
    manifest_dependencies,
    override_problems,
    ownership_problems,
    parse_overrides,
    parse_stages,
    recheck_note,
    required_go_live_ids,
    requirement_ids,
    section_override,
    size_problems,
    stage_problems,
    traits_line_problems,
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


def table(*rows, size="small", method="normal", extra=(), cycle=1):
    given = dict(rows)
    body = [given.get(n) or f"| {STAGE_NAMES[n]} | open | - | - |" for n in range(8)]
    head = [f"Size: {size}", f"Method: {method}", f"Cycle: {cycle}", *extra, "",
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


def grill_section(heading, rows=3, by="mattpocock-skills:grilling", answer="Only the shop owner uses it.",
                  outcome="kept as it is"):
    lines = [f"## {heading}", "", f"Grilled with: {by}", "",
             "| Challenge | Owner's answer | Outcome |", "|---|---|---|"]
    lines += [f"| Challenge {i}? | {answer} | {outcome} |" for i in range(1, rows + 1)]
    return "\n".join(lines) + "\n"


GRILL_OK = "# Grilling\n\n" + grill_section("Intake") + "\n" + grill_section("Design")
EV0 = "file:REQUIREMENTS.md,file:ATTACKS.md,file:GRILLING.md"
EV1 = "file:DECISIONS.md,file:GRILLING.md"
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
        self.root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "GRILLING.md": GRILL_OK,
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
        self.assertEqual(self.check(self.stage0(EV0)), [])

    def test_spaces_after_the_comma_are_fine(self):
        self.assertEqual(self.check(self.stage0("file:REQUIREMENTS.md, file:ATTACKS.md, file:GRILLING.md")), [])

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
        problems = self.check(self.stage0(r"file:docs\a.md,file:REQUIREMENTS.md,file:ATTACKS.md,file:GRILLING.md"))
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


class CycleRules(GitCase):
    """The Cycle line: the start of a cycle is the oldest commit whose STAGES.md holds the current Cycle value."""

    def two_cycle_repo(self, one_commit):
        """Work done in cycle 1, then a second cycle started in one commit or in two (remove, then add)."""
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"STAGES.md": table(cycle=1)}, "setup")
        old_work = commit(root, {"BUILD-LEDGER.md": LEDGER_OK, "app.py": "x = 1\n"}, "work in cycle one")
        if not one_commit:
            commit(root, remove=("STAGES.md",), message="archive the first cycle")
        start = commit(root, {"STAGES.md": table(cycle=2)}, "second cycle setup")
        return root, old_work, start

    def stage3(self, root, commit_hash, cycle=2):
        text = table(row(3, "passed", f"commit:{commit_hash},file:BUILD-LEDGER.md"), cycle=cycle)
        return stage_problems(text, root, ls(root), {})

    def test_cycle_line_is_parsed(self):
        self.assertEqual(parse_stages(table(cycle=3)).cycle, 3)

    def test_missing_cycle_line_is_a_problem(self):
        stages = parse_stages(table().replace("Cycle: 1\n", ""))
        self.assertTrue(any("Cycle" in m for _, m in stages.errors), stages.errors)

    def test_malformed_cycle_lines_are_problems_at_their_line(self):
        for bad in ("Cycle: x", "Cycle: 0", "Cycle: -1", "Cycle: 1.5", "Cycle:"):
            with self.subTest(bad=bad):
                text = table().replace("Cycle: 1", bad)
                stages = parse_stages(text)
                self.assertIn(line_of(text, bad), [n for n, m in stages.errors if "Cycle" in m], stages.errors)
                self.assertIsNone(stages.cycle)

    def test_a_second_cycle_line_is_a_problem(self):
        stages = parse_stages(table(extra=("Cycle: 2",)))
        self.assertTrue(any("twice" in m for _, m in stages.errors), stages.errors)

    def test_a_cycle_line_inside_a_comment_does_not_count(self):
        stages = parse_stages("<!--\nCycle: 5\n-->\n" + table().replace("Cycle: 1\n", ""))
        self.assertIsNone(stages.cycle)

    def test_a_stages_file_without_cycle_is_reported_by_the_project_check(self):
        root = self.make_repo({"README.md": "x\n"})
        commit(root, {"STAGES.md": table().replace("Cycle: 1\n", "")}, "setup")
        self.assertTrue(any("Cycle" in p.message for p in check_project(root)[0]))

    def test_start_is_the_oldest_commit_that_holds_the_value(self):
        root = self.make_repo({"README.md": "x\n"})
        first = commit(root, {"STAGES.md": table(cycle=1)}, "setup")
        commit(root, {"STAGES.md": table(row(0, "adopted"), cycle=1, extra=("Adopted-at: 1",))}, "edit")
        self.assertEqual(cycle_start(root, "STAGES.md", 1), first)

    def test_start_of_a_one_commit_new_cycle_is_that_commit(self):
        root, _, start = self.two_cycle_repo(one_commit=True)
        self.assertEqual(cycle_start(root, "STAGES.md", 2), start)
        self.assertNotEqual(cycle_start(root, "STAGES.md", 1), start)

    def test_start_skips_the_commit_that_removed_the_file(self):
        root, _, start = self.two_cycle_repo(one_commit=False)
        self.assertEqual(cycle_start(root, "STAGES.md", 2), start)

    def test_no_cycle_value_gives_none_even_when_history_exists(self):
        root, _, _ = self.two_cycle_repo(one_commit=True)
        self.assertIsNone(cycle_start(root, "STAGES.md", None))

    def test_a_file_committed_without_a_cycle_line_has_no_start(self):
        root = self.make_repo({"README.md": "x\n"})
        commit(root, {"STAGES.md": table().replace("Cycle: 1\n", "")}, "old format")
        self.assertIsNone(cycle_start(root, "STAGES.md", None))

    def test_no_commit_holding_the_value_gives_none(self):
        root, _, _ = self.two_cycle_repo(one_commit=True)
        self.assertIsNone(cycle_start(root, "STAGES.md", 3))
        self.assertIsNone(cycle_start(root, "NOPE.md", 1))

    def test_one_commit_new_cycle_no_longer_lets_old_commits_count(self):
        root, old_work, _ = self.two_cycle_repo(one_commit=True)
        self.assertTrue(any("no listed commit was made after" in m for m in messages(self.stage3(root, old_work))))

    def test_two_commit_new_cycle_no_longer_lets_old_commits_count(self):
        root, old_work, _ = self.two_cycle_repo(one_commit=False)
        self.assertTrue(any("no listed commit was made after" in m for m in messages(self.stage3(root, old_work))))

    def test_a_commit_made_after_the_new_cycle_started_counts_in_both_flows(self):
        for one_commit in (True, False):
            with self.subTest(one_commit=one_commit):
                root, _, _ = self.two_cycle_repo(one_commit)
                new_work = commit(root, {"more.py": "y = 2\n"}, "work in cycle two")
                self.assertFalse(any("after" in m for m in messages(self.stage3(root, new_work))))

    def test_adopted_at_in_a_later_cycle_fires_even_when_that_cycle_starts_with_it(self):
        root = self.make_repo({"README.md": "x\n", "app.py": "x = 1\n"})
        commit(root, {"STAGES.md": table(row(0, "adopted"), row(1, "adopted"), extra=("Adopted-at: 2",))}, "one")
        rows = [row(n, "adopted") for n in range(4)]
        text = table(*rows, cycle=2, extra=("Adopted-at: 4",))
        commit(root, {"STAGES.md": text}, "second cycle in one commit")
        problems = stage_problems(text, root, ls(root), {})
        self.assertIn(line_of(text, "Adopted-at: 4"), [p.line for p in problems if "cycle 1" in p.message], problems)

    def test_changing_adopted_at_inside_one_cycle_still_fires(self):
        root = self.make_repo({"README.md": "x\n", "app.py": "x = 1\n"})
        commit(root, {"STAGES.md": table(row(0, "adopted"), row(1, "adopted"), extra=("Adopted-at: 2",))}, "one")
        text = table(*[row(n, "adopted") for n in range(4)], extra=("Adopted-at: 4",))
        problems = stage_problems(text, root, ls(root), {})
        self.assertTrue(any("first commit" in m for m in messages(problems)), problems)

    def test_the_source_before_adoption_check_looks_before_the_first_commit_that_added_stages(self):
        root = self.make_repo({"README.md": "x\n"})
        commit(root, {"STAGES.md": table()}, "setup")
        commit(root, {"app.py": "x = 1\n"}, "code arrives in cycle one")
        text = table(*[row(n, "adopted") for n in range(2)], cycle=2, extra=("Adopted-at: 2",))
        commit(root, {"STAGES.md": text}, "second cycle with adoption")
        self.assertTrue(any("source" in m for m in messages(stage_problems(text, root, ls(root), {}))))

    def test_adoption_with_no_source_before_the_current_cycle_start_fires(self):
        root = self.make_repo({"README.md": "x\n"})
        commit(root, {"STAGES.md": table()}, "setup")
        text = table(*[row(n, "adopted") for n in range(2)], cycle=2, extra=("Adopted-at: 2",))
        commit(root, {"STAGES.md": text}, "second cycle with adoption")
        self.assertTrue(any("source" in m for m in messages(stage_problems(text, root, ls(root), {}))))


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

    def test_hand_raising_the_cycle_to_adopt_a_new_project_fires(self):
        """Review repro: init, then code, then Cycle: 2 and Adopted-at: 5 written by hand. Both guards used to pass."""
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"STAGES.md": STAGES_OPEN}, "init")
        commit(root, {"main.py": "print(1)\n"}, "code")
        text = table(*[row(n, "adopted") for n in range(5)], cycle=2, extra=("Adopted-at: 5",))
        commit(root, {"STAGES.md": text}, "bump")
        problems = check_project(root)[0]
        self.assert_mentions(problems, "cycle 1")
        self.assert_mentions(problems, "first commit")
        self.assert_mentions(problems, "source")

    def test_hand_adding_adopted_at_in_cycle_1_after_the_first_commit_still_fires(self):
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"STAGES.md": STAGES_OPEN}, "init")
        commit(root, {"main.py": "print(1)\n"}, "code")
        text = table(*[row(n, "adopted") for n in range(5)], extra=("Adopted-at: 5",))
        commit(root, {"STAGES.md": text}, "adopt by hand")
        self.assert_mentions(check_project(root)[0], "first commit")

    def test_a_genuine_adoption_in_cycle_1_passes(self):
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"main.py": "print(1)\n"}, "code that existed before the process")
        text = table(*[row(n, "adopted") for n in range(5)], extra=("Adopted-at: 5",))
        commit(root, {"STAGES.md": text}, "adopt at stage 5")
        self.assertEqual(stage_problems(text, root, ls(root), {}), [])

    def test_a_later_cycle_of_an_adopted_project_without_adopted_at_passes(self):
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"main.py": "print(1)\n"}, "code")
        commit(root, {"STAGES.md": table(*[row(n, "adopted") for n in range(2)], extra=("Adopted-at: 2",))}, "adopt")
        text = table(cycle=2)
        commit(root, {"STAGES.md": text}, "second cycle")
        self.assertEqual(stage_problems(text, root, ls(root), {}), [])

    def test_adoption_is_anchored_to_the_first_add_even_after_the_file_was_removed_and_added_again(self):
        root = self.make_repo({"README.md": "# p\n"})
        commit(root, {"STAGES.md": STAGES_OPEN}, "init")
        commit(root, remove=("STAGES.md",), message="remove")
        commit(root, {"main.py": "print(1)\n"}, "code")
        text = table(*[row(n, "adopted") for n in range(2)], extra=("Adopted-at: 2",))
        commit(root, {"STAGES.md": text}, "add again with adoption")
        problems = stage_problems(text, root, ls(root), {})
        self.assert_mentions(problems, "first commit")
        self.assert_mentions(problems, "source")

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
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "GRILLING.md": GRILL_OK})
        self.assertEqual(self.run_check(root, 0, "small", EV0), [])

    def test_stage_1_decisions_without_entry_fires(self):
        root = self.make_repo({"DECISIONS.md": "# Decisions\n"})
        self.assert_mentions(self.run_check(root, 1, "small", "file:DECISIONS.md"), "entry")

    def test_stage_1_small_with_entry_passes(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "GRILLING.md": GRILL_OK})
        self.assertEqual(self.run_check(root, 1, "small", EV1), [])

    def test_stage_1_full_needs_a_design_file(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK})
        self.assert_mentions(self.run_check(root, 1, "full", "file:DECISIONS.md"), "design")

    def test_stage_1_full_plan_file_is_not_a_design(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/plans/p.md": "plan\n"})
        self.assert_mentions(self.run_check(root, 1, "full", "file:DECISIONS.md,file:docs/plans/p.md"), "design")

    def test_stage_1_full_with_design_passes(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/design.md": "design\n", "GRILLING.md": GRILL_OK})
        self.assertEqual(self.run_check(root, 1, "full", EV1 + ",file:docs/design.md"), [])

    # ---- grilling: on every project, Small and Full, at stage 0 and stage 1
    def test_grilling_is_required_at_stages_0_and_1_on_both_sizes(self):
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "DECISIONS.md": DECISIONS_OK,
                               "docs/design.md": "design\n"})
        for stage, evidence in ((0, "file:REQUIREMENTS.md,file:ATTACKS.md"), (1, "file:DECISIONS.md")):
            for size in ("small", "full"):
                with self.subTest(stage=stage, size=size):
                    extra = ",file:docs/design.md" if (stage, size) == (1, "full") else ""
                    self.assert_mentions(self.run_check(root, stage, size, evidence + extra), "GRILLING.md")

    def test_grilling_passes_at_stage_0_and_1_when_recorded(self):
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "DECISIONS.md": DECISIONS_OK,
                               "GRILLING.md": GRILL_OK})
        self.assertEqual(self.run_check(root, 0, "small", EV0), [])
        self.assertEqual(self.run_check(root, 1, "small", EV1), [])

    def test_stage_0_judges_only_the_intake_section(self):
        text = "# Grilling\n\n" + grill_section("Intake")
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "DECISIONS.md": DECISIONS_OK,
                               "GRILLING.md": text})
        self.assertEqual(self.run_check(root, 0, "small", EV0), [])
        self.assert_mentions(self.run_check(root, 1, "small", EV1), "Design")

    def test_too_few_grilling_rows_fail_on_small_too(self):
        text = "# Grilling\n\n" + grill_section("Intake", rows=2)
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "GRILLING.md": text})
        self.assert_mentions(self.run_check(root, 0, "small", EV0), "at least 3")

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
        root = self.make_repo({"AI-Agents.md": "# AI log\n", "DECISIONS.md": DECISIONS_OK, "GRILLING.md": GRILL_OK})
        self.assertEqual(self.run_check(root, 1, "small", "file:AI-Agents.md," + EV1), [])


class MarkerRules(GitCase):
    """The template marker counts only outside comments and code fences, and a bad evidence file is reported once."""

    MARKED = "(EXAMPLE)"

    def item(self, text, name="REQUIREMENTS.md"):
        root = self.make_repo({name: text})
        return check_gates.evidence_item_problems("file", name, root, set(ls(root)))

    def about(self, problems, name):
        return [p for p in problems if p.file == name or name in p.message]

    def test_a_marker_in_a_table_row_is_refused(self):
        found = self.item(f"| ID | Requirement |\n|---|---|\n| REQ-1 | It works. {self.MARKED} |\n")
        self.assertTrue(any(self.MARKED in m for m in found), found)

    def test_a_marker_only_inside_a_one_line_comment_is_not_refused(self):
        text = f"<!-- rows marked {self.MARKED}: replace them -->\n| ID | Requirement |\n|---|---|\n| REQ-1 | It works. |\n"
        self.assertEqual(self.item(text), [])

    def test_a_marker_only_inside_a_multi_line_comment_is_not_refused(self):
        text = (f"<!--\nThe rows below are worked examples, marked\n{self.MARKED}: replace them and remove the marker.\n"
                "-->\n\n| ID | Requirement |\n|---|---|\n| REQ-1 | It works. |\n")
        self.assertEqual(self.item(text), [])

    def test_a_marker_after_a_closed_comment_on_the_same_line_is_refused(self):
        found = self.item(f"<!-- note --> | REQ-1 | It works. {self.MARKED} |\n")
        self.assertTrue(any(self.MARKED in m for m in found), found)

    def test_an_empty_evidence_file_is_reported_once(self):
        for stage, name in ((0, "REQUIREMENTS.md"), (1, "DECISIONS.md"), (3, "BUILD-LEDGER.md"), (7, "AI-Agents.md")):
            with self.subTest(name=name):
                root = self.make_repo({name: "\n"})
                problems = stage_problems(table(row(stage, "passed", f"file:{name}")), root, ls(root), {})
                self.assertEqual(len(self.about(problems, name)), 1, problems)

    def test_a_marker_bearing_evidence_file_is_reported_once(self):
        root = self.make_repo({"DECISIONS.md": f"# Decisions\n\nNothing decided yet {self.MARKED}\n"})
        problems = stage_problems(table(row(1, "passed", "file:DECISIONS.md")), root, ls(root), {})
        self.assertEqual(len(self.about(problems, "DECISIONS.md")), 1, problems)
        self.assert_mentions(problems, self.MARKED)

    def test_a_good_evidence_file_still_gets_its_content_rule(self):
        root = self.make_repo({"DECISIONS.md": "# Decisions\n\nNothing decided yet.\n"})
        problems = stage_problems(table(row(1, "passed", "file:DECISIONS.md")), root, ls(root), {})
        self.assert_mentions(problems, "no decision entry")

    def ownership_stage(self, stage, explain, full):
        root = self.make_repo({"OWNERSHIP.md": ownership_doc(full=full, explain=explain)})
        return stage_problems(table(row(stage, "passed", "file:OWNERSHIP.md")), root, ls(root), {})

    def marked_rounds(self):
        return [(f"Question {i}? {self.MARKED}", "An answer.", "-", "closed") for i in range(1, 4)]

    def test_stage_5_does_not_judge_the_marker_in_the_full_round(self):
        problems = self.ownership_stage(5, EB_OK, self.marked_rounds())
        self.assertFalse(any(self.MARKED in m for m in messages(problems)), problems)

    def test_stage_5_refuses_the_marker_in_the_explain_back(self):
        explain = [EB_OK[0], EB_OK[1], ("how-to-recover", f"Question? {self.MARKED}", "An answer.", "-", "closed")]
        self.assert_mentions(self.ownership_stage(5, explain, fr_rows(3)), self.MARKED)

    def test_stage_6_refuses_the_marker_in_the_full_round(self):
        self.assert_mentions(self.ownership_stage(6, EB_OK, self.marked_rounds()), self.MARKED)

    def test_full_round_rows_with_the_marker_never_count_as_answered(self):
        root = self.make_repo({"src/app.py": "x = 1\n"})
        sha = git(root, "rev-parse", "HEAD")
        problems = ownership_problems(ownership_doc(full=self.marked_rounds(), commit=sha), root, ls(root), "small", 1,
                                      {})
        self.assert_mentions(problems, "0 answered questions")

    def test_full_round_rows_without_the_marker_count_as_answered(self):
        root = self.make_repo({"src/app.py": "x = 1\n"})
        sha = git(root, "rev-parse", "HEAD")
        self.assertEqual(ownership_problems(ownership_doc(commit=sha), root, ls(root), "small", 1, {}), [])


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
        out.append(section("Components", md_table(COMP_COLS, [(c, "does work") for c in comps])))
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


# ----------------------------------------------------- traits, size and go-live

TRAIT_DEPS = {
    "database": ("psycopg", "psycopg2-binary", "asyncpg", "sqlalchemy", "prisma", "pg", "mysql2"),
    "web": ("flask", "fastapi", "django", "streamlit", "express", "next"),
    "llm": ("anthropic", "openai", "langchain", "litellm", "@anthropic-ai/sdk"),
    "paid-api": ("stripe", "twilio"),
    "scheduled": ("celery", "apscheduler"),
}


def stage_doc(size="small", extra=()):
    return parse_stages(table(size=size, extra=extra))


class TraitRules(GitCase):
    def detect(self, tracked=(), deps=None):
        return detect_traits(Path("."), list(tracked), deps or {})

    def test_a_dockerfile_in_a_real_repository_means_container(self):
        root = self.make_repo({"Dockerfile": "FROM base\n"})
        self.assertEqual(detect_traits(root, ls(root), {}), {"container"})

    def test_container_file_names(self):
        for name in ("Dockerfile", "svc/Dockerfile", "Dockerfile.dev", "api.dockerfile", "compose.yaml",
                     "compose.override.yml", "docker-compose.yml", "ops/docker-compose.prod.yaml"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), {"container"})

    def test_documents_and_other_tools_named_like_containers_are_not_containers(self):
        for name in ("Dockerfile.md", "docs/Dockerfile.txt", "composer.yml", "composer.yaml", "compose.yml.md",
                     "docker-composer.yml"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), set())
                self.assertEqual(size_problems(parse_stages(table()), [name], set()), [])

    def test_look_alike_names_are_not_containers(self):
        for name in ("README.md", "compose.txt", "composer.json", "docs/Dockerfile-notes.md", "compose.py"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), set())

    def test_sql_file_and_migrations_folder_mean_database(self):
        for name in ("schema.sql", "db/seed.SQL", "migrations/0001_init.py", "app/migrations/0002.py"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), {"database"})

    def test_look_alike_database_names_are_not_database(self):
        for name in ("notes.sqlx", "my_migrations/a.py", "migrations.md", "sql/readme.txt"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), set())

    def test_crontab_file_means_scheduled(self):
        for name in ("crontab", "ops/crontab"):
            with self.subTest(name=name):
                self.assertEqual(self.detect([name]), {"scheduled"})

    def test_each_listed_dependency_gives_its_trait(self):
        for trait, deps in TRAIT_DEPS.items():
            for dep in deps:
                with self.subTest(trait=trait, dep=dep):
                    expected = {trait} | ({"paid-api"} if trait == "llm" else set())
                    self.assertEqual(self.detect(deps={dep: None}), expected)

    def test_anthropic_dependency_is_llm_and_paid_api(self):
        self.assertEqual(self.detect(deps={"anthropic": None}), {"llm", "paid-api"})

    def test_unlisted_dependency_gives_nothing(self):
        self.assertEqual(self.detect(["README.md"], {"rich": None}), set())

    def test_dependency_names_are_compared_in_normal_form(self):
        self.assertEqual(self.detect(deps={"Psycopg2_Binary": "2.9.9"}), {"database"})

    def test_traits_from_files_and_dependencies_add_up(self):
        got = self.detect(["Dockerfile", "schema.sql"], {"flask": "3.0.0", "anthropic": None})
        self.assertEqual(got, {"container", "database", "web", "llm", "paid-api"})

    def test_files_inside_node_modules_are_ignored(self):
        self.assertEqual(self.detect(["node_modules/pkg/Dockerfile", "node_modules/pkg/a.sql"]), set())


class SizeRules(GitCase):
    def check(self, size="small", tracked=(), traits=()):
        return size_problems(stage_doc(size), list(tracked), set(traits))

    def test_small_with_a_dockerfile_names_it(self):
        self.assert_mentions(self.check(tracked=["Dockerfile", "a.py"]), "Dockerfile")

    def test_small_with_a_compose_file_names_it(self):
        self.assert_mentions(self.check(tracked=["compose.yaml"]), "compose")

    def test_small_with_a_dockerfile_in_a_folder_names_the_path(self):
        self.assert_mentions(self.check(tracked=["svc/Dockerfile"]), "svc/Dockerfile")

    def test_eleven_source_files_name_the_limit(self):
        self.assert_mentions(self.check(tracked=[f"src/f{i}.py" for i in range(11)]), "10")

    def test_ten_source_files_pass(self):
        self.assertEqual(self.check(tracked=[f"src/f{i}.py" for i in range(10)]), [])

    def test_only_source_extensions_are_counted(self):
        self.assertEqual(self.check(tracked=[f"docs/n{i}.md" for i in range(30)] + ["a.py"]), [])

    def test_mixed_source_extensions_are_counted_together(self):
        self.assert_mentions(self.check(tracked=[f"a{i}.py" for i in range(6)] + [f"b{i}.ts" for i in range(5)]), "10")

    def test_llm_trait_is_refused_on_small(self):
        self.assert_mentions(self.check(tracked=["a.py"], traits={"llm", "paid-api"}), "llm")

    def test_personal_data_trait_is_refused_on_small(self):
        self.assert_mentions(self.check(tracked=["a.py"], traits={"personal-data"}), "personal-data")

    def test_web_trait_is_refused_on_small(self):
        self.assert_mentions(self.check(tracked=["a.py"], traits={"web"}), "web")

    def test_paid_api_trait_is_refused_on_small(self):
        self.assert_mentions(self.check(tracked=["a.py"], traits={"paid-api"}), "paid-api")

    def test_database_and_scheduled_traits_alone_are_allowed_on_small(self):
        self.assertEqual(self.check(tracked=["a.py"], traits={"database", "scheduled"}), [])

    def test_full_is_never_refused(self):
        tracked = ["Dockerfile", "compose.yml"] + [f"src/f{i}.py" for i in range(30)]
        self.assertEqual(self.check("full", tracked, {"web", "llm", "paid-api", "personal-data"}), [])

    def test_problems_sit_on_the_size_line(self):
        problems = self.check(tracked=["Dockerfile"])
        self.assertEqual({p.line for p in problems}, {line_of(table(), "Size:")})
        self.assertEqual({p.file for p in problems}, {"STAGES.md"})

    def test_a_small_clean_project_passes(self):
        self.assertEqual(self.check(tracked=["a.py", "README.md"]), [])

    def test_each_refusal_is_its_own_problem(self):
        problems = self.check(tracked=["Dockerfile"] + [f"f{i}.py" for i in range(11)], traits={"web", "llm"})
        self.assertEqual(len(problems), 4)


class TraitsLineRules(GitCase):
    def test_manual_manifests_without_a_traits_line_fire(self):
        self.assert_mentions(traits_line_problems(stage_doc(), [], True), "Traits")

    def test_unreadable_manifest_without_a_traits_line_fires(self):
        self.assert_mentions(traits_line_problems(stage_doc(), ["go.mod"], False), "Traits")

    def test_traits_none_satisfies_the_rule(self):
        self.assertEqual(traits_line_problems(stage_doc(extra=("Traits: none",)), ["go.mod"], False), [])

    def test_listed_traits_satisfy_the_rule(self):
        self.assertEqual(traits_line_problems(stage_doc(extra=("Traits: web",)), [], True), [])

    def test_readable_manifests_need_no_traits_line(self):
        self.assertEqual(traits_line_problems(stage_doc(), [], False), [])


CHECKLIST_ALWAYS = {"id": "C-SEC-1", "applies_when": ["always"]}
CHECKLIST_LLM = {"id": "C-LLM-1", "applies_when": ["llm"]}
CHECKLIST_WEB = {"id": "C-WEB-1", "applies_when": ["web"]}
CHECKLIST_EITHER = {"id": "C-DB-1", "applies_when": ["database", "scheduled"]}
GL_COLS = ["Risk", "Validation", "Source", "Status", "Evidence"]


def gl_rows(*cells):
    return "# Go-live\n\n" + md_table(GL_COLS, cells)


def golive_ok(ids):
    return gl_rows(*[(f"risk {i}", f"check {i}", i, "proven", "ran x: 0 hits") for i in ids])


class GoLiveRules(GitCase):
    def check(self, text, required, overrides=None):
        return go_live_problems(text, set(required), overrides or {})

    # ---- which ids are required
    def test_required_ids_are_always_items_matching_items_and_attacks(self):
        got = required_go_live_ids({"llm"}, [CHECKLIST_ALWAYS, CHECKLIST_LLM, CHECKLIST_WEB], {"ATK-1"})
        self.assertEqual(got, {"C-SEC-1", "C-LLM-1", "ATK-1"})

    def test_an_item_for_another_trait_is_not_required(self):
        self.assertNotIn("C-WEB-1", required_go_live_ids({"llm"}, [CHECKLIST_WEB], set()))

    def test_with_no_traits_only_always_items_and_attacks_are_required(self):
        got = required_go_live_ids(set(), [CHECKLIST_ALWAYS, CHECKLIST_LLM], {"ATK-1", "ATK-2"})
        self.assertEqual(got, {"C-SEC-1", "ATK-1", "ATK-2"})

    def test_one_matching_trait_is_enough(self):
        self.assertEqual(required_go_live_ids({"scheduled"}, [CHECKLIST_EITHER], set()), {"C-DB-1"})

    def test_an_item_that_applies_to_nothing_is_never_required(self):
        item = {"id": "C-X-1", "applies_when": []}
        self.assertEqual(required_go_live_ids({"web", "llm"}, [item], set()), set())

    def test_nothing_required_when_nothing_given(self):
        self.assertEqual(required_go_live_ids(set(), [], set()), set())

    # ---- source cells
    def test_two_ids_in_one_source_cell_fire(self):
        text = gl_rows(("r", "v", "C-X-1, ATK-1", "proven", "ran x: 0 hits"))
        self.assert_mentions(self.check(text, {"C-X-1", "ATK-1"}), "one id per row")

    def test_a_longer_attack_id_does_not_cover_a_shorter_one(self):
        text = gl_rows(("r", "v", "ATK-10", "proven", "ran x: 0 hits"))
        self.assert_mentions(self.check(text, {"ATK-1"}), "ATK-1 has no row")

    def test_free_text_source_leaves_the_required_id_without_a_row(self):
        text = gl_rows(("r", "v", "s", "proven", "ran x: 0 hits"))
        self.assert_mentions(self.check(text, {"ATK-2"}), "ATK-2")

    def test_a_row_with_free_text_source_is_allowed_beside_the_required_rows(self):
        text = gl_rows(("r", "v", "C-X-1", "proven", "ran x: 0 hits"),
                       ("port 80 is open", "scan the host", "proposed for this project", "proven", "ran y: closed"))
        self.assertEqual(self.check(text, {"C-X-1"}), [])

    def test_source_in_backticks_still_matches(self):
        text = gl_rows(("r", "v", "`C-X-1`", "proven", "ran x: 0 hits"))
        self.assertEqual(self.check(text, {"C-X-1"}), [])

    def test_two_rows_for_one_required_id_fire(self):
        text = gl_rows(("r", "v", "C-X-1", "proven", "ran x: 0 hits"), ("r2", "v2", "C-X-1", "proven", "ran z: 0"))
        self.assert_mentions(self.check(text, {"C-X-1"}), "more than one row")

    def test_a_missing_required_id_is_named(self):
        text = golive_ok(["C-X-1"])
        problems = self.check(text, {"C-X-1", "ATK-3"})
        self.assert_mentions(problems, "ATK-3 has no row")
        self.assertFalse(any("C-X-1" in m for m in messages(problems)))

    # ---- status
    def test_open_row_is_unresolved(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "open", "")), {"C-X-1"}), "unresolved")

    def test_blank_status_is_unresolved(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "", "ran x")), {"C-X-1"}), "unresolved")

    def test_unknown_status_is_unresolved(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "done", "ran x")), {"C-X-1"}), "unresolved")

    def test_proven_without_evidence_fires(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "proven", "")), {"C-X-1"}), "evidence")

    def test_proven_with_a_placeholder_evidence_fires(self):
        for filler in ("-", "n/a", "TBD", "..."):
            with self.subTest(filler=filler):
                self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "proven", filler)), {"C-X-1"}), "evidence")

    def test_proven_with_evidence_passes(self):
        self.assertEqual(self.check(golive_ok(["C-X-1"]), {"C-X-1"}), [])

    def test_not_applicable_without_a_reason_fires(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "not applicable", "")), {"C-X-1"}), "reason")

    def test_not_applicable_with_a_reason_passes(self):
        text = gl_rows(("r", "v", "C-X-1", "not applicable", "no network access exists in this tool"))
        self.assertEqual(self.check(text, {"C-X-1"}), [])

    def test_overridden_with_an_override_that_does_not_exist_names_it(self):
        self.assert_mentions(self.check(gl_rows(("r", "v", "C-X-1", "overridden", "O2")), {"C-X-1"}), "O2")

    def test_overridden_with_an_open_override_for_ship_passes(self):
        text = gl_rows(("r", "v", "C-X-1", "overridden", "O2"))
        self.assertEqual(self.check(text, {"C-X-1"}, {"O2": ov("open", "5 Ship")}), [])

    def test_overridden_with_an_override_for_another_stage_fires(self):
        text = gl_rows(("r", "v", "C-X-1", "overridden", "O2"))
        self.assert_mentions(self.check(text, {"C-X-1"}, {"O2": ov("open", "3 Build")}), "O2")

    def test_overridden_with_a_closed_override_fires(self):
        text = gl_rows(("r", "v", "C-X-1", "overridden", "O2"))
        self.assert_mentions(self.check(text, {"C-X-1"}, {"O2": ov("closed", "5 Ship")}), "O2")

    def test_overridden_without_an_override_id_in_evidence_fires(self):
        text = gl_rows(("r", "v", "C-X-1", "overridden", "the owner agreed"))
        self.assert_mentions(self.check(text, {"C-X-1"}, {"O2": ov("open", "5 Ship")}), "override")

    # ---- shape
    def test_no_rows_fires(self):
        self.assert_mentions(self.check(gl_rows(), set()), "no rows")

    def test_blank_risk_validation_or_source_fires(self):
        for cells, label in ((("", "v", "C-X-1", "proven", "ran x"), "Risk"),
                             (("r", "", "C-X-1", "proven", "ran x"), "Validation"),
                             (("r", "v", "", "proven", "ran x"), "Source")):
            with self.subTest(label=label):
                self.assert_mentions(self.check(gl_rows(cells), {"C-X-1"}), label)

    def test_wrong_columns_are_reported(self):
        text = "# Go-live\n\n| Risk | Check |\n|---|---|\n| a | b |\n"
        self.assert_mentions(self.check(text, set()), "columns")

    def test_a_row_inside_a_comment_does_not_count(self):
        text = "# Go-live\n\n<!--\n" + md_table(GL_COLS, [("r", "v", "C-X-1", "proven", "ran x")]) + "-->\n"
        self.assertTrue(self.check(text, {"C-X-1"}))

    def test_example_marker_fires(self):
        text = gl_rows(("risk (EXAMPLE)", "v", "C-X-1", "proven", "ran x: 0 hits"))
        self.assert_mentions(self.check(text, {"C-X-1"}), "(EXAMPLE)")

    def test_bom_and_crlf_change_nothing(self):
        text = gl_rows(("r", "v", "C-X-1", "open", ""), ("r", "v", "C-X-2", "proven", "ran x"))
        plain = self.check(text, {"C-X-1", "C-X-2"})
        self.assertTrue(plain)
        self.assertEqual(self.check(BOM + text.replace("\n", "\r\n"), {"C-X-1", "C-X-2"}), plain)

    def test_garbage_never_raises(self):
        for text in ("", "\x00|||\n| |\n", "|" * 5000, "| Risk | Validation | Source | Status | Evidence |\n| a |\n",
                     gl_rows(("r",) * 5) * 50):
            with self.subTest(size=len(text)):
                self.check(text, {"C-X-1"})


TOPICS = ("what-it-does", "how-it-breaks", "how-to-recover")
EB_COLS = ["Topic", "Question", "Answer", "Gap", "Status"]
FR_COLS = ["Question", "Answer", "Gap", "Status"]


def eb_row(topic, answer="It reads the file and writes a report", gap="-", status="closed"):
    return (topic, f"Question about {topic}?", answer, gap, status)


EB_OK = [eb_row(t) for t in TOPICS]


def explain_doc(rows, override=None):
    top = f"Override: {override}\n\n" if override else ""
    return "# Ownership\n\n## Explain-back\n\n" + top + md_table(EB_COLS, rows)


def fr_rows(count, answer="It keeps the records between runs", gap="-", status="closed"):
    return [(f"Question {i}?", answer, gap, status) for i in range(1, count + 1)]


def ownership_doc(full=None, explain=None, commit="abc1234", closed="2026-01-01", due="2026-01-08", done="-",
                  graded="fresh session, 2026-01-01", override=None, skip=()):
    top = f"Override: {override}\n\n" if override else ""
    lines = (("Hand-changed commit", commit), ("Closed", closed), ("Re-check due", due), ("Re-check done", done),
             ("Graded by", graded))
    body = "\n".join(f"{label}: {value}" for label, value in lines if label not in skip)
    parts = ["# Ownership\n"]
    if explain is not None:
        parts.append("## Explain-back\n\n" + md_table(EB_COLS, explain))
    rows = fr_rows(3) if full is None else full
    parts.append("## Full round\n\n" + top + md_table(FR_COLS, rows) + "\n" + body + "\n")
    return "\n".join(parts)


class ExplainBackRules(GitCase):
    def check(self, text, overrides=None):
        return explain_back_problems(text, overrides or {})

    def test_a_missing_topic_is_named(self):
        self.assert_mentions(self.check(explain_doc(EB_OK[:2])), "how-to-recover")

    def test_a_blank_answer_fires(self):
        rows = [EB_OK[0], eb_row("how-it-breaks", answer=""), EB_OK[2]]
        self.assert_mentions(self.check(explain_doc(rows)), "answer")

    def test_a_placeholder_answer_fires(self):
        rows = [EB_OK[0], eb_row("how-it-breaks", answer="TBD"), EB_OK[2]]
        self.assert_mentions(self.check(explain_doc(rows)), "answer")

    def test_an_open_gap_fires(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="did not know about the backup", status="open")]
        self.assert_mentions(self.check(explain_doc(rows)), "gap")

    def test_three_closed_answers_pass(self):
        self.assertEqual(self.check(explain_doc(EB_OK)), [])

    def test_a_closed_gap_with_text_passes(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="missed the backup step, now explained")]
        self.assertEqual(self.check(explain_doc(rows)), [])

    def test_a_blank_gap_cell_fires(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="")]
        self.assert_mentions(self.check(explain_doc(rows)), "Gap")

    def test_a_status_other_than_open_or_closed_fires(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", status="done")]
        self.assert_mentions(self.check(explain_doc(rows)), "Status")

    def test_an_unknown_topic_fires(self):
        rows = EB_OK + [eb_row("what-it-costs")]
        self.assert_mentions(self.check(explain_doc(rows)), "what-it-costs")

    def test_an_open_override_for_ship_silences_an_open_gap(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="unsure", status="open")]
        self.assertEqual(self.check(explain_doc(rows, "O1"), {"O1": ov("open", "5 Ship")}), [])

    def test_an_override_for_another_stage_does_not_silence(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="unsure", status="open")]
        problems = self.check(explain_doc(rows, "O1"), {"O1": ov("open", "6 Own")})
        self.assert_mentions(problems, "O1")
        self.assert_mentions(problems, "gap")

    def test_an_unknown_override_is_named_and_the_gap_still_counts(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="unsure", status="open")]
        problems = self.check(explain_doc(rows, "O9"))
        self.assert_mentions(problems, "O9")
        self.assert_mentions(problems, "gap")

    def test_a_missing_section_is_a_problem(self):
        self.assert_mentions(self.check("# Ownership\n\n## Full round\n\n"), "Explain-back")

    def test_an_example_marker_fires(self):
        rows = [EB_OK[0], EB_OK[1], ("how-to-recover", "Question? (EXAMPLE)", "an answer", "-", "closed")]
        self.assert_mentions(self.check(explain_doc(rows)), "(EXAMPLE)")

    def test_bom_and_crlf_change_nothing(self):
        text = explain_doc(EB_OK[:2])
        self.assertEqual(self.check(BOM + text.replace("\n", "\r\n")), self.check(text))
        self.assertTrue(self.check(text))

    def test_garbage_never_raises(self):
        for text in ("", "## Explain-back\n", "## Explain-back\n|||\n|\n", "\x00" * 100,
                     "## Explain-back\n\n" + "| a |\n" * 500):
            with self.subTest(size=len(text)):
                self.check(text)


class OwnershipRules(GitCase):
    def setUp(self):
        self.root = self.make_repo({"README.md": "# p\n"})
        self.base = git(self.root, "rev-parse", "HEAD")
        self.src = commit(self.root, {"src/app.py": "x = 1\n"}, "hand change")
        self.docs = commit(self.root, {"README.md": "# changed\n"}, "docs only")

    def check(self, text, size="small", comps=1, overrides=None):
        return ownership_problems(text, self.root, ls(self.root), size, comps, overrides or {})

    def doc(self, **given):
        given.setdefault("commit", self.src)
        return ownership_doc(**given)

    # ---- the full round
    def test_a_complete_document_passes(self):
        self.assertEqual(self.check(self.doc()), [])

    def test_two_answers_on_small_name_the_minimum(self):
        self.assert_mentions(self.check(self.doc(full=fr_rows(2))), "at least 3")

    def test_three_answers_on_small_pass(self):
        self.assertEqual(self.check(self.doc(full=fr_rows(3))), [])

    def test_small_does_not_scale_with_components(self):
        self.assertEqual(self.check(self.doc(full=fr_rows(3)), "small", 9), [])

    def test_four_answers_on_full_with_six_components_name_six(self):
        self.assert_mentions(self.check(self.doc(full=fr_rows(4)), "full", 6), "at least 6")

    def test_six_answers_on_full_with_six_components_pass(self):
        self.assertEqual(self.check(self.doc(full=fr_rows(6)), "full", 6), [])

    def test_full_with_two_components_still_needs_three(self):
        self.assert_mentions(self.check(self.doc(full=fr_rows(2)), "full", 2), "at least 3")
        self.assertEqual(self.check(self.doc(full=fr_rows(3)), "full", 2), [])

    def test_blank_answers_fire_and_do_not_count(self):
        rows = fr_rows(2) + [("Question 3?", "", "-", "closed")]
        problems = self.check(self.doc(full=rows))
        self.assert_mentions(problems, "answer is blank")
        self.assert_mentions(problems, "at least 3")

    def test_an_open_gap_fires(self):
        rows = fr_rows(2) + [("Question 3?", "a wrong guess", "mixed up two modules", "open")]
        self.assert_mentions(self.check(self.doc(full=rows)), "gap")

    def test_a_closed_gap_passes(self):
        rows = fr_rows(2) + [("Question 3?", "a first guess", "mixed up two modules; explained again", "closed")]
        self.assertEqual(self.check(self.doc(full=rows)), [])

    def test_a_blank_gap_cell_fires(self):
        self.assert_mentions(self.check(self.doc(full=fr_rows(3, gap=""))), "Gap")

    def test_a_status_other_than_open_or_closed_fires(self):
        self.assert_mentions(self.check(self.doc(full=fr_rows(3, status="maybe"))), "Status")

    def test_a_blank_question_fires(self):
        rows = fr_rows(2) + [("", "an answer", "-", "closed")]
        self.assert_mentions(self.check(self.doc(full=rows)), "Question")

    def test_an_open_override_for_own_silences_the_table(self):
        rows = fr_rows(1, gap="unsure", status="open")
        problems = self.check(self.doc(full=rows, override="O1"), overrides={"O1": ov("open", "6 Own")})
        self.assertEqual(problems, [])

    def test_the_override_does_not_silence_the_lines(self):
        problems = self.check(self.doc(full=fr_rows(1), override="O1", skip=("Graded by",)),
                              overrides={"O1": ov("open", "6 Own")})
        self.assert_mentions(problems, "Graded by")

    def test_an_override_for_another_stage_does_not_silence(self):
        problems = self.check(self.doc(full=fr_rows(1), override="O1"), overrides={"O1": ov("open", "5 Ship")})
        self.assert_mentions(problems, "O1")
        self.assert_mentions(problems, "at least 3")

    def test_a_missing_full_round_section_is_a_problem(self):
        self.assert_mentions(self.check("# Ownership\n\nGraded by: someone\n"), "Full round")

    def test_an_example_marker_fires(self):
        rows = fr_rows(2) + [("Question 3? (EXAMPLE)", "an answer", "-", "closed")]
        self.assert_mentions(self.check(self.doc(full=rows)), "(EXAMPLE)")

    # ---- the hand change
    def test_a_commit_that_is_not_a_hash_fires(self):
        self.assert_mentions(self.check(self.doc(commit="not-a-hash")), "commit")

    def test_a_hash_that_does_not_exist_fires(self):
        self.assert_mentions(self.check(self.doc(commit="abcdef1")), "commit")

    def test_a_commit_missing_from_the_document_is_named(self):
        self.assert_mentions(self.check(self.doc(skip=("Hand-changed commit",))), "Hand-changed commit")

    def test_a_blank_commit_fires(self):
        self.assert_mentions(self.check(self.doc(commit="")), "commit")

    def test_a_commit_touching_only_a_readme_fires(self):
        self.assert_mentions(self.check(self.doc(commit=self.docs)), "source file")

    def test_a_root_commit_with_only_a_readme_fires(self):
        self.assert_mentions(self.check(self.doc(commit=self.base)), "source file")

    def test_a_commit_on_another_branch_is_not_in_history(self):
        git(self.root, "checkout", "-q", "-b", "side")
        side = commit(self.root, {"src/side.py": "y = 2\n"}, "on a side branch")
        git(self.root, "checkout", "-q", "-")
        self.assert_mentions(self.check(self.doc(commit=side)), "history")

    def test_a_short_hash_works(self):
        self.assertEqual(self.check(self.doc(commit=self.src[:8])), [])

    def test_a_commit_touching_a_notebook_counts_as_source(self):
        nb = commit(self.root, {"analysis.ipynb": "{}\n"}, "notebook")
        self.assertEqual(self.check(self.doc(commit=nb)), [])

    # ---- graded by, closed and the re-check dates
    def test_a_missing_graded_by_line_is_named(self):
        self.assert_mentions(self.check(self.doc(skip=("Graded by",))), "Graded by")

    def test_a_placeholder_graded_by_fires(self):
        for filler in ("", "-", "TBD"):
            with self.subTest(filler=filler):
                self.assert_mentions(self.check(self.doc(graded=filler)), "Graded by")

    def test_a_recheck_date_eight_days_after_closing_fires(self):
        self.assert_mentions(self.check(self.doc(closed="2026-01-01", due="2026-01-09")), "7 days")

    def test_a_recheck_date_six_days_after_closing_fires(self):
        self.assert_mentions(self.check(self.doc(closed="2026-01-01", due="2026-01-07")), "7 days")

    def test_a_recheck_date_exactly_seven_days_after_closing_passes(self):
        self.assertEqual(self.check(self.doc(closed="2026-02-25", due="2026-03-04")), [])

    def test_a_recheck_date_before_closing_fires(self):
        self.assert_mentions(self.check(self.doc(closed="2026-01-10", due="2026-01-03")), "7 days")

    def test_a_closing_date_that_is_not_a_date_fires(self):
        for bad in ("soon", "2026-13-01", "01/02/2026", ""):
            with self.subTest(bad=bad):
                self.assert_mentions(self.check(self.doc(closed=bad)), "Closed")

    def test_a_missing_due_line_is_named(self):
        self.assert_mentions(self.check(self.doc(skip=("Re-check due",))), "Re-check due")

    def test_a_recheck_done_value_must_be_a_dash_or_a_date(self):
        self.assert_mentions(self.check(self.doc(done="yes")), "Re-check done")
        self.assertEqual(self.check(self.doc(done="2026-01-09")), [])
        self.assertEqual(self.check(self.doc(done="-")), [])

    def test_lines_inside_a_comment_do_not_count(self):
        text = "# Ownership\n\n## Full round\n\n" + md_table(FR_COLS, fr_rows(3)) + "\n<!--\n" + \
               "\n".join(f"{k}: x" for k in ("Hand-changed commit", "Closed", "Re-check due", "Re-check done",
                                              "Graded by")) + "\n-->\n"
        messages_ = messages(self.check(text))
        for label in ("Hand-changed commit", "Closed", "Re-check due", "Re-check done", "Graded by"):
            with self.subTest(label=label):
                self.assertTrue(any(label in m for m in messages_), messages_)

    def test_bom_and_crlf_change_nothing(self):
        text = self.doc(full=fr_rows(2), graded="")
        self.assertTrue(self.check(text))
        self.assertEqual(self.check(BOM + text.replace("\n", "\r\n")), self.check(text))

    def test_garbage_never_raises(self):
        for text in ("", "## Full round\n", "\x00|||\n", "Graded by:" * 400, "## Full round\n\n" + "| a |\n" * 500):
            with self.subTest(size=len(text)):
                self.check(text)


class NulInGitArguments(GitCase):
    def test_a_commit_value_with_a_nul_is_a_failed_lookup_not_a_crash(self):
        """Found by the robustness fuzz on 2026-11-10: 'commit:<hash>\\x00...' in STAGES.md reached git and raised."""
        root = self.make_repo()
        self.assertIsNone(check_gates.resolve_commit(root, "abc1234\x00def"))
        self.assertNotEqual(check_gates.git(root, "rev-parse", "a\x00b").returncode, 0)


class GrillingRules(unittest.TestCase):
    """GRILLING.md: the owner grilled on the requirements (Intake) and the design (Design), on every project."""

    def check(self, text, section="Intake"):
        return grilling_problems(text, section)

    def test_a_complete_section_passes(self):
        self.assertEqual(self.check(GRILL_OK, "Intake"), [])
        self.assertEqual(self.check(GRILL_OK, "Design"), [])

    def test_a_missing_section_is_named(self):
        self.assertTrue(any("Design" in m for m in self.check("# Grilling\n\n" + grill_section("Intake"), "Design")))

    def test_two_rows_are_not_enough(self):
        self.assertTrue(any("at least 3" in m for m in self.check("# G\n\n" + grill_section("Intake", rows=2))))

    def test_three_rows_are_enough(self):
        self.assertEqual(self.check("# G\n\n" + grill_section("Intake", rows=3)), [])

    def test_a_blank_answer_fires_and_does_not_count(self):
        problems = self.check("# G\n\n" + grill_section("Intake", answer=""))
        self.assertTrue(any("answer" in m for m in problems), problems)
        self.assertTrue(any("at least 3" in m for m in problems), problems)

    def test_a_placeholder_answer_fires(self):
        self.assertTrue(any("answer" in m for m in self.check("# G\n\n" + grill_section("Intake", answer="TBD"))))

    def test_a_blank_outcome_fires(self):
        self.assertTrue(any("Outcome" in m for m in self.check("# G\n\n" + grill_section("Intake", outcome=""))))

    def test_the_grilled_with_line_must_be_filled(self):
        for by in ("", "-"):
            with self.subTest(by=by):
                self.assertTrue(any("Grilled with" in m
                                    for m in self.check("# G\n\n" + grill_section("Intake", by=by))))
        missing = "# G\n\n" + grill_section("Intake").replace("Grilled with: mattpocock-skills:grilling\n", "")
        self.assertTrue(any("Grilled with" in m for m in self.check(missing)))

    def test_the_fallback_counts_as_a_method(self):
        self.assertEqual(self.check("# G\n\n" + grill_section("Intake", by="fallback: written challenges")), [])

    def test_a_grilled_with_line_in_the_other_section_does_not_count(self):
        text = "# G\n\n" + grill_section("Intake").replace("Grilled with: mattpocock-skills:grilling\n", "") + \
               "\n" + grill_section("Design")
        self.assertTrue(any("Grilled with" in m for m in self.check(text, "Intake")))

    def test_wrong_columns_fire(self):
        text = "# G\n\n## Intake\n\nGrilled with: x\n\n| Q | A |\n|---|---|\n| a | b |\n"
        self.assertTrue(self.check(text))

    def test_garbage_never_raises(self):
        for text in ("", "## Intake\n", "## Intake\n|||\n", "\x00" * 50, "## Intake\n\n" + "| a |\n" * 300):
            with self.subTest(size=len(text)):
                self.check(text)


class RecheckNote(unittest.TestCase):
    def lines(self, due, done="-", closed="2026-01-01"):
        return f"Closed: {closed}\nRe-check due: {due}\nRe-check done: {done}\n"

    def test_an_overdue_recheck_is_noted(self):
        note = recheck_note(self.lines("2026-01-08"), date(2026, 1, 9))
        self.assertIn("re-check", note)
        self.assertIn("2026-01-08", note)

    def test_the_due_day_itself_is_silent(self):
        """Design section 7: the re-check is asked the first time the owner works in the project after that date."""
        self.assertIsNone(recheck_note(self.lines("2026-01-08"), date(2026, 1, 8)))

    def test_a_recheck_not_yet_due_is_silent(self):
        self.assertIsNone(recheck_note(self.lines("2026-01-08"), date(2026, 1, 7)))

    def test_a_recheck_marked_done_is_silent(self):
        self.assertIsNone(recheck_note(self.lines("2026-01-08", done="2026-01-09"), date(2026, 1, 9)))

    def test_a_missing_done_line_counts_as_not_done(self):
        self.assertIn("re-check", recheck_note("Re-check due: 2026-01-08\n", date(2026, 1, 9)))

    def test_a_missing_or_invalid_due_date_is_silent(self):
        for text in ("", "Closed: 2026-01-01\n", self.lines("soon"), self.lines("2026-13-40")):
            with self.subTest(text=text):
                self.assertIsNone(recheck_note(text, date(2030, 1, 1)))

    def test_a_line_inside_a_comment_does_not_count(self):
        self.assertIsNone(recheck_note("<!--\n" + self.lines("2026-01-08") + "-->\n", date(2026, 1, 9)))

    def test_bom_and_crlf_change_nothing(self):
        text = self.lines("2026-01-08")
        self.assertEqual(recheck_note(BOM + text.replace("\n", "\r\n"), date(2026, 1, 9)),
                         recheck_note(text, date(2026, 1, 9)))


CHECKLIST_OK = json.dumps([CHECKLIST_ALWAYS, CHECKLIST_LLM, CHECKLIST_WEB])
THREE_ATTACKS = attack_doc(0, size_rows=[("ATK-1", "a", "3", "x"), ("ATK-2", "b", "-", "x"), ("ATK-3", "c", "-", "x")])


class GoLiveTiming(GitCase):
    """Whole projects through check_project: which check binds at which stage."""
    TODAY = date(2026, 1, 3)

    def project(self, through=6, size="small", comps=("Parser",), stage5="file:OWNERSHIP.md,file:GO-LIVE.md",
                golive=None, explain=None, rounds=None, checklist=CHECKLIST_OK, traits_line=None, extra=None,
                deps=(), hand="src", overrides=None, ship_override=False, ownership_lines=None, manual=None):
        """A consistent project (Small by default) whose stages 0 to `through` are passed; arguments break one thing."""
        big = size == "full"
        root = self.make_repo({"README.md": "# p\n"})
        base = git(root, "rev-parse", "HEAD")
        commit(root, {"STAGES.md": table()}, "stages")
        built = commit(root, {"src/app.py": "x = 1\n", E: "x = 1\n"}, "built")
        attack_rows = [(f"ATK-{i}", "an attack", "3" if i == 1 else "-", "x") for i in range(1, 6 if big else 4)]
        attack_names = [r[0] for r in attack_rows]
        files = {"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": attack_doc(0, size_rows=attack_rows),
                 "DECISIONS.md": DECISIONS_OK, "BUILD-LEDGER.md": LEDGER_OK, "GRILLING.md": GRILL_OK,
                 "GO-LIVE.md": golive or golive_ok(["C-SEC-1", *attack_names]),
                 "OWNERSHIP.md": ownership_doc(explain=EB_OK if explain is None else explain, full=rounds,
                                               commit={"src": built, "base": base}[hand],
                                               **(ownership_lines or {}))}
        if big:
            files.update({"docs/design.md": "design\n", "docs/plans/p.md": "plan\n", "RESULTS.md": "results\n"})
        else:
            files["PLAN.md"] = "tasks\n"
        if checklist is not None:
            files["checks/checklist.json"] = checklist
        if overrides is not None:
            files["OVERRIDES.md"] = overrides
        files.update(extra or {})
        names = sorted(set(files) | {"README.md", "STAGES.md", "ARCHITECTURE.md", "src/app.py", E})
        parts = [*comps, "REQ-1", *attack_names]
        tests = [trow(p, *((E,) * 5 if big else (E, E, E if p == "ATK-1" else "", "", ""))) for p in parts]
        files["ARCHITECTURE.md"] = doc(comps=list(comps), map=names, deps=list(deps), tests=tests, manual=manual)
        evidence = {0: EV0,
                    1: EV1 + (",file:docs/design.md" if big else ""),
                    2: "file:docs/plans/p.md" if big else "file:PLAN.md",
                    3: f"commit:{built},file:BUILD-LEDGER.md",
                    4: "file:ARCHITECTURE.md" + (",file:RESULTS.md" if big else ""), 5: stage5,
                    6: "file:OWNERSHIP.md"}
        rows = [row(n, "passed", evidence[n]) for n in range(through + 1)]
        if ship_override:
            rows[5] = row(5, "overridden", "-", "O1")
        extra_lines = () if traits_line is None else (f"Traits: {traits_line}",)
        files["STAGES.md"] = table(*rows, size=size, extra=extra_lines)
        commit(root, files, "documents")
        return root

    def run_all(self, root, today=None):
        return check_project(root, today or self.TODAY)

    def only(self, root, name, today=None):
        return [p for p in self.run_all(root, today)[0] if p.file == name]

    # ---- a complete project
    def test_a_complete_project_has_no_problems_and_no_notes(self):
        self.assertEqual(self.run_all(self.project()), ([], []))

    def test_an_overdue_recheck_is_a_note_and_not_a_problem(self):
        problems, notes = self.run_all(self.project(), date(2026, 1, 9))
        self.assertEqual(problems, [])
        self.assertTrue(any("re-check" in n for n in notes), notes)

    def test_a_recheck_not_yet_due_gives_no_note(self):
        self.assertEqual(self.run_all(self.project(), date(2026, 1, 7))[1], [])

    def test_a_done_recheck_gives_no_note(self):
        root = self.project(ownership_lines={"done": "2026-01-08"})
        self.assertEqual(self.run_all(root, date(2026, 1, 9)), ([], []))

    def test_no_recheck_note_before_stage_6_is_passed(self):
        root = self.project(through=5)
        self.assertEqual(self.run_all(root, date(2026, 1, 9))[1], [])

    # ---- the go-live review
    def test_stage_5_evidence_must_name_go_live_when_rows_are_required(self):
        root = self.project(stage5="file:OWNERSHIP.md", traits_line="scheduled")
        problems = self.only(root, "STAGES.md")
        self.assert_mentions(problems, "GO-LIVE.md")

    def test_a_missing_attack_row_is_reported_at_stage_5(self):
        root = self.project(golive=golive_ok(["C-SEC-1", "ATK-1", "ATK-3"]), traits_line="scheduled")
        self.assert_mentions(self.only(root, "GO-LIVE.md"), "ATK-2")

    def test_an_unresolved_row_is_reported_at_stage_5(self):
        rows = [("r", "v", i, "proven", "ran x") for i in ("C-SEC-1", "ATK-1", "ATK-2")]
        root = self.project(golive=gl_rows(*rows, ("r", "v", "ATK-3", "open", "")), traits_line="scheduled")
        self.assert_mentions(self.only(root, "GO-LIVE.md"), "unresolved")

    # ---- which projects need the go-live file (design section 4)
    def test_small_with_no_traits_does_not_need_go_live_in_the_evidence(self):
        root = self.project(stage5="file:OWNERSHIP.md")
        self.assertEqual(self.only(root, "STAGES.md"), [])

    def test_small_with_no_traits_is_not_judged_on_a_go_live_file_it_happens_to_have(self):
        root = self.project(golive=gl_rows(("r", "v", "ATK-1", "open", "")))
        self.assertEqual(self.only(root, "GO-LIVE.md"), [])

    def test_small_declared_none_does_not_need_go_live(self):
        root = self.project(stage5="file:OWNERSHIP.md", traits_line="none")
        self.assertEqual(self.only(root, "STAGES.md"), [])

    def test_small_with_a_detected_trait_still_needs_go_live(self):
        root = self.project(stage5="file:OWNERSHIP.md", extra={"crontab": "0 1 * * * run\n"})
        self.assert_mentions(self.only(root, "STAGES.md"), "GO-LIVE.md")

    def test_full_with_no_traits_still_needs_go_live(self):
        root = self.project(size="full", stage5="file:OWNERSHIP.md", rounds=fr_rows(3))
        self.assert_mentions(self.only(root, "STAGES.md"), "GO-LIVE.md")

    def test_small_with_no_traits_still_has_its_attacks_checked_in_the_test_table(self):
        root = self.project(stage5="file:OWNERSHIP.md")
        text = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
        kept = "".join(line for line in text.splitlines(keepends=True) if not line.startswith("| ATK-2 |"))
        self.assertNotEqual(kept, text)
        commit(root, {"ARCHITECTURE.md": kept}, "drop one attack row")
        self.assert_mentions(self.only(root, "ARCHITECTURE.md"), "ATK-2")

    def test_the_go_live_file_is_not_judged_before_stage_5_is_passed(self):
        root = self.project(through=4, golive=gl_rows(), checklist=None)
        self.assertEqual(self.only(root, "GO-LIVE.md"), [])
        self.assertEqual(self.only(root, "checks/checklist.json"), [])
        self.assertEqual(self.only(root, "STAGES.md"), [])

    def test_a_missing_checklist_is_a_problem_once_stage_5_is_passed(self):
        root = self.project(checklist=None)
        problems = self.only(root, "checks/checklist.json")
        self.assertEqual([p.line for p in problems], [0])
        self.assert_mentions(problems, "missing")

    def test_a_malformed_checklist_is_a_problem_not_a_crash(self):
        for name, text in (("not json", "{oops"), ("not a list", '{"id": "x"}'), ("item without id", '[{"applies_when": []}]'),
                           ("item without applies_when", '[{"id": "C-1"}]'), ("applies_when not a list",
                                                                               '[{"id": "C-1", "applies_when": "web"}]'),
                           ("deep nesting", "[" * 100000), ("not utf-8", None)):
            with self.subTest(case=name):
                root = self.project(checklist=text if text is not None else b"[\xff]")
                self.assertTrue(self.only(root, "checks/checklist.json"))

    def test_a_checklist_with_a_byte_order_mark_and_crlf_is_fine(self):
        text = BOM + json.dumps([CHECKLIST_ALWAYS, CHECKLIST_LLM], indent=2).replace("\n", "\r\n")
        self.assertEqual(self.only(self.project(checklist=text), "checks/checklist.json"), [])

    def test_a_declared_trait_adds_its_checklist_rows(self):
        root = self.project(traits_line="web")
        self.assert_mentions(self.only(root, "GO-LIVE.md"), "C-WEB-1")

    def test_a_detected_trait_adds_its_checklist_rows(self):
        root = self.project(extra={"requirements.txt": "anthropic==1.0\n"}, deps=["anthropic 1.0"])
        self.assert_mentions(self.only(root, "GO-LIVE.md"), "C-LLM-1")

    def test_a_trait_with_a_row_in_the_go_live_file_passes(self):
        ids = ["C-SEC-1", "C-LLM-1", "ATK-1", "ATK-2", "ATK-3"]
        root = self.project(extra={"requirements.txt": "anthropic==1.0\n"}, deps=["anthropic 1.0"],
                            golive=golive_ok(ids))
        self.assertEqual(self.only(root, "GO-LIVE.md"), [])

    def test_an_unreadable_manifest_needs_a_traits_line_at_stage_5(self):
        root = self.project(extra={"go.mod": "module x\n"})
        self.assert_mentions(self.only(root, "STAGES.md"), "Traits")
        fixed = self.project(extra={"go.mod": "module x\n"}, traits_line="none")
        self.assertFalse(any("Traits" in m for m in messages(self.only(fixed, "STAGES.md"))))

    def test_manual_manifests_need_a_traits_line_at_stage_5(self):
        root = self.project(manual="build scripts are vendored")
        self.assert_mentions(self.only(root, "STAGES.md"), "Traits")
        fixed = self.project(manual="build scripts are vendored", traits_line="none")
        self.assertFalse(any("Traits" in m for m in messages(self.only(fixed, "STAGES.md"))))

    def test_stage_5_passed_with_ownership_file_missing_is_reported_without_a_crash(self):
        root = self.project()
        git(root, "rm", "-q", "--", "OWNERSHIP.md")
        problems = self.run_all(root)[0]
        self.assertTrue(any("OWNERSHIP.md" in m for m in messages(problems)), problems)

    # ---- the explain-back
    def test_an_open_explain_back_gap_blocks_stage_5(self):
        rows = [EB_OK[0], EB_OK[1], eb_row("how-to-recover", gap="did not know", status="open")]
        self.assert_mentions(self.only(self.project(explain=rows), "OWNERSHIP.md"), "gap")

    def test_a_missing_explain_back_topic_blocks_stage_5(self):
        self.assert_mentions(self.only(self.project(explain=EB_OK[:2]), "OWNERSHIP.md"), "how-to-recover")

    def test_the_explain_back_is_not_judged_before_stage_5(self):
        root = self.project(through=4, explain=[])
        self.assertEqual(self.only(root, "OWNERSHIP.md"), [])

    def test_an_overridden_ship_stage_skips_the_explain_back_and_go_live(self):
        overrides = overrides_doc(entry(1, stage="5 Ship", reconfirmed="2026-01-02"))
        rows = [eb_row("what-it-does", status="open", gap="unsure")]
        root = self.project(ship_override=True, overrides=overrides, explain=rows, golive=gl_rows(), checklist=None)
        self.assertEqual(self.run_all(root), ([], ["open override O1 (stage 5 Ship): see OVERRIDES.md"]))

    def test_an_overridden_ship_stage_still_needs_the_override_reconfirmed(self):
        overrides = overrides_doc(entry(1, stage="5 Ship"))
        root = self.project(ship_override=True, overrides=overrides, golive=gl_rows(), checklist=None)
        self.assert_mentions(self.only(root, "OVERRIDES.md"), "O1")

    # ---- the full round
    def test_the_full_round_binds_at_stage_6_and_not_before(self):
        self.assertEqual(self.only(self.project(through=5, rounds=[]), "OWNERSHIP.md"), [])
        self.assertTrue(self.only(self.project(through=6, rounds=[]), "OWNERSHIP.md"))

    def test_too_few_full_round_answers_are_reported_at_stage_6(self):
        self.assert_mentions(self.only(self.project(rounds=fr_rows(2)), "OWNERSHIP.md"), "at least 3")

    def test_a_hand_change_that_touches_no_source_is_reported_at_stage_6(self):
        self.assert_mentions(self.only(self.project(hand="base"), "OWNERSHIP.md"), "source file")

    def test_a_complete_full_project_has_no_problems(self):
        self.assertEqual(self.run_all(self.project(size="full", rounds=fr_rows(3)))[0], [])

    def test_a_full_project_needs_one_answer_per_component(self):
        comps = ("Parser", "Store", "Exporter", "Reader")
        short = self.project(size="full", comps=comps, rounds=fr_rows(3))
        self.assert_mentions(self.only(short, "OWNERSHIP.md"), "at least 4")
        enough = self.project(size="full", comps=comps, rounds=fr_rows(4))
        self.assertEqual(self.only(enough, "OWNERSHIP.md"), [])

    def test_a_small_project_does_not_scale_with_components(self):
        root = self.project(comps=("Parser", "Store", "Exporter", "Reader"), rounds=fr_rows(3))
        self.assertEqual(self.only(root, "OWNERSHIP.md"), [])

    # ---- the size rule
    def test_small_with_a_dockerfile_is_refused_through_check_project(self):
        root = self.make_repo({"STAGES.md": table(), "Dockerfile": "FROM base\n"})
        self.assert_mentions(self.only(root, "STAGES.md"), "Dockerfile")

    def test_full_with_a_dockerfile_is_not_refused(self):
        root = self.make_repo({"STAGES.md": table(size="full"), "Dockerfile": "FROM base\n"})
        self.assertEqual(self.only(root, "STAGES.md"), [])

    def test_small_with_a_detected_llm_dependency_is_refused(self):
        root = self.make_repo({"STAGES.md": table(), "requirements.txt": "anthropic==1.0\n"})
        self.assert_mentions(self.only(root, "STAGES.md"), "llm")

    def test_small_with_a_declared_personal_data_trait_is_refused(self):
        root = self.make_repo({"STAGES.md": table(extra=("Traits: personal-data",))})
        self.assert_mentions(self.only(root, "STAGES.md"), "personal-data")

    def test_small_with_eleven_tracked_source_files_is_refused(self):
        files = {"STAGES.md": table(), **{f"src/f{i}.py": "x = 1\n" for i in range(11)}}
        self.assert_mentions(self.only(self.make_repo(files), "STAGES.md"), "10")


class GoLiveCommand(GitCase):
    def repo(self, checklist=True):
        files = {"STAGES.md": table(size="full", extra=("Traits: personal-data",)), "ATTACKS.md": THREE_ATTACKS,
                 "requirements.txt": "anthropic==1.0\n", "Dockerfile": "FROM base\n"}
        if checklist:
            files["checks/checklist.json"] = CHECKLIST_OK
        return self.make_repo(files)

    def test_it_prints_the_traits_and_the_required_ids_and_exits_0(self):
        code, out, _ = run_main(["--go-live", str(self.repo())])
        self.assertEqual(code, 0)
        self.assertIn("traits: container, llm, paid-api, personal-data", out.splitlines())
        for needle in ("C-SEC-1", "C-LLM-1", "ATK-1", "ATK-2", "ATK-3"):
            self.assertIn(needle, out.split())
        self.assertNotIn("C-WEB-1", out)

    def test_the_folder_may_come_before_the_flag(self):
        self.assertEqual(run_main([str(self.repo()), "--go-live"])[0], 0)

    def test_it_exits_0_although_the_project_has_problems(self):
        root = self.make_repo({"STAGES.md": table(row(0, "passed"), size="full"), "ATTACKS.md": THREE_ATTACKS})
        self.assertTrue(check_project(root)[0])
        self.assertEqual(run_main(["--go-live", str(root)])[0], 0)

    def test_without_a_checklist_it_lists_the_attacks_and_says_so_on_stderr(self):
        code, out, err = run_main(["--go-live", str(self.repo(checklist=False))])
        self.assertEqual(code, 0)
        self.assertIn("ATK-1", out.split())
        self.assertNotIn("C-SEC-1", out)
        self.assertIn("checklist", err)

    def test_no_traits_prints_none(self):
        root = self.make_repo({"STAGES.md": table(), "a.py": "x = 1\n"})
        code, out, _ = run_main(["--go-live", str(root)])
        self.assertEqual(code, 0)
        self.assertIn("traits: none", out.splitlines())

    def test_small_with_no_traits_is_told_the_file_is_not_required(self):
        root = self.make_repo({"STAGES.md": table(), "ATTACKS.md": THREE_ATTACKS,
                               "checks/checklist.json": CHECKLIST_OK})
        code, out, _ = run_main(["--go-live", str(root)])
        self.assertEqual(code, 0)
        self.assertIn("required ids (0):", out.splitlines())
        self.assertIn("GO-LIVE.md is not required", out)
        self.assertNotIn("ATK-1", out.split())

    def test_small_with_a_declared_trait_still_lists_the_ids(self):
        root = self.make_repo({"STAGES.md": table(extra=("Traits: scheduled",)), "ATTACKS.md": THREE_ATTACKS,
                               "checks/checklist.json": CHECKLIST_OK})
        out = run_main(["--go-live", str(root)])[1]
        self.assertIn("ATK-1", out.split())
        self.assertNotIn("not required", out)

    def test_not_a_directory_or_too_many_arguments_exit_2(self):
        self.assertEqual(run_main(["--go-live", str(ROOT / "nope-folder")])[0], 2)
        self.assertEqual(run_main(["--go-live", "a", "b"])[0], 2)

    def test_not_a_git_repository_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_main(["--go-live", tmp])[0], 2)


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
        self.assertIn("not a git repository", err)         # the trust-limit note on stderr also says "git"

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


# ------------------------------------------------------------ closing survivors of the rule-removal run (RESULTS.md)
# Each test below was written because removing one rule from a copy of the gate left every earlier test green.

class TextHelperRules(unittest.TestCase):
    def test_a_comment_keeps_its_line_breaks_so_line_numbers_stay_true(self):
        self.assertEqual(check_gates.clean_lines("a <!-- x\ny\nz --> b\nc"), ["a ", "", " b", "c"])

    def test_dash_dash_dash_is_not_a_comment_opener_with_a_closer(self):
        self.assertEqual(check_gates.clean_lines("a <!--->\nb"), ["a <!--->", "b"])

    def test_a_short_opener_is_not_a_comment(self):
        self.assertEqual(check_gates.clean_lines("<!- x -->"), ["<!- x -->"])

    def test_an_unclosed_comment_is_left_in_place(self):
        self.assertEqual(check_gates.clean_lines("a <!-- open\nb"), ["a <!-- open", "b"])

    def test_a_fenced_block_is_blanked(self):
        self.assertEqual(check_gates.clean_lines("```py\nx\n```\ny"), ["", "", "", "y"])

    def test_a_shorter_fence_does_not_close_a_longer_one(self):
        text = "````\ncode\n```\nstill code\n````\nafter"
        self.assertEqual(check_gates.clean_lines(text), ["", "", "", "", "", "after"])

    def test_a_closing_fence_carries_no_text(self):
        text = "```\ncode\n``` not a closer\nmore\n```\nafter"
        self.assertEqual(check_gates.clean_lines(text), ["", "", "", "", "", "after"])

    def test_split_row_drops_the_outer_pipes_and_trims(self):
        self.assertEqual(check_gates.split_row("| a | b |"), ["a", "b"])

    def test_split_row_keeps_an_escaped_pipe_inside_a_cell(self):
        self.assertEqual(check_gates.split_row("| a \\| b | c |"), ["a \\| b", "c"])

    def test_split_row_does_not_treat_a_final_escaped_pipe_as_a_border(self):
        self.assertEqual(check_gates.split_row("| a | b \\|"), ["a", "b \\|"])

    def test_alignment_rows_need_a_dash_in_every_cell(self):
        self.assertTrue(check_gates.is_alignment_row(["---", ":-:", "--:"]))
        self.assertFalse(check_gates.is_alignment_row([""]))
        self.assertFalse(check_gates.is_alignment_row(["::"]))
        self.assertFalse(check_gates.is_alignment_row(["---", "text"]))

    def test_section_lines_stop_at_a_level_two_heading(self):
        self.assertEqual(check_gates.section_lines("## A\nx\n## B\ny", "A"), ["x"])
        self.assertEqual(check_gates.section_lines("## A\nx\n# T\ny", "A"), ["x"])
        self.assertEqual(check_gates.section_lines("## A\nx\n### sub\ny", "A"), ["x", "### sub", "y"])

    def test_is_date_accepts_only_the_dashed_iso_form(self):
        self.assertTrue(check_gates._is_date("2026-11-09"))
        self.assertFalse(check_gates._is_date("20261109"))
        self.assertFalse(check_gates._is_date("2026-W45-1"))
        self.assertFalse(check_gates._is_date("2026-13-45"))


class EvidenceCellRules(GitCase):
    def test_a_file_item_with_no_path_is_an_error(self):
        for cell in ("file:", "file:   ", "commit:"):
            items, errors = check_gates.parse_evidence(cell)
            self.assertEqual((items, len(errors)), ([], 1), cell)

    def test_a_dash_or_blank_cell_holds_no_items_and_no_errors(self):
        for cell in ("-", "", "  -  "):
            self.assertEqual(check_gates.parse_evidence(cell), ([], []), repr(cell))

    def test_a_missing_file_reads_as_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(check_gates.read_evidence_file(Path(tmp), "nope.md"))

    def test_a_passed_stage_with_no_evidence_says_so(self):
        root = self.make_repo()
        text = table(row(2, "passed", "-"))
        self.assert_mentions(stage_problems(text, root, ls(root), {}), "names no evidence")

    def test_a_build_row_without_a_commit_names_the_missing_commit(self):
        root = self.make_repo({"BUILD-LEDGER.md": LEDGER_OK})
        text = table(row(3, "passed", "file:BUILD-LEDGER.md"))
        self.assert_mentions(stage_problems(text, root, ls(root), {}), "'commit:<hash>'")

    def test_a_build_row_before_stages_md_is_committed_says_so(self):
        root = self.make_repo({"BUILD-LEDGER.md": LEDGER_OK})
        text = table(row(3, "passed", f"commit:{git(root, 'rev-parse', 'HEAD')},file:BUILD-LEDGER.md"))
        self.assert_mentions(stage_problems(text, root, ls(root), {}), "not committed yet")

    def test_wrong_stage_table_columns_are_named(self):
        text = ("Size: small\nMethod: normal\nCycle: 1\n\n| Name | State | Proof | Override |\n|---|---|---|---|\n"
                "| 0 Intake | open | - | - |\n")
        self.assertTrue(any("columns must be exactly" in m for _, m in parse_stages(text).errors))

    def test_a_reviews_table_with_the_wrong_columns_is_refused(self):
        text = "# L\n\n## Reviews\n\n| A | B | C |\n|---|---|---|\n| 1 | x | y |\n"
        self.assertTrue(any("columns" in m for m in check_gates.ledger_problems(text)))


class RungCellRules(GitCase):
    """A rung cell must name test evidence: the gate's own records, ARCHITECTURE.md and empty files are not."""

    def setUp(self):
        self.root = self.make_repo({"README.md": "# p\n", "ARCHITECTURE.md": "# a\n", "STAGES.md": STAGES_OPEN,
                                    "OVERRIDES.md": "# o\n", "docs/archive/STAGES-cycle-1.md": STAGES_OPEN,
                                    "tests/test_a.py": "import unittest\n", "tests/test_empty.py": "",
                                    "tests/test_blank.py": "  \n"})
        self.tracked = set(ls(self.root))

    def rung(self, cell):
        return check_gates._rung_problem(cell, self.root, self.tracked)

    def test_the_gate_records_and_the_architecture_file_are_refused(self):
        for cell in ("STAGES.md", "OVERRIDES.md", "ARCHITECTURE.md", "docs/archive/STAGES-cycle-1.md"):
            with self.subTest(cell=cell):
                self.assertIn("cannot be rung evidence", self.rung(cell) or "")

    def test_an_empty_tracked_file_is_refused(self):
        for cell in ("tests/test_empty.py", "tests/test_blank.py"):
            with self.subTest(cell=cell):
                self.assertIn("cannot be rung evidence", self.rung(cell) or "")

    def test_a_tracked_test_file_still_counts(self):
        self.assertIsNone(self.rung("tests/test_a.py"))
        self.assertIsNone(self.rung("tests/test_a.py::test_one"))

    def test_n_a_with_a_reason_still_counts(self):
        self.assertIsNone(self.rung("n/a: reads a file only"))

    def test_a_refused_file_beside_a_real_test_file_counts_for_the_test_file(self):
        self.assertIsNone(self.rung("STAGES.md, tests/test_a.py"))

    def test_the_review_row_naming_the_gate_files_is_refused(self):
        doc_text = doc(tests=[trow("REQ-1", "ARCHITECTURE.md", "STAGES.md", "README.md", "README.md", "README.md")])
        problems = tt_problems(doc_text, "full", {"REQ-1"}, {}, ls(self.root), self.root, {})
        self.assertEqual(sorted(m.split(":")[1].strip() for m in messages(problems) if "cannot be rung" in m),
                         ["rung 1 (Written first)", "rung 2 (Catches breakage)"], problems)


class ComponentSectionRules(GitCase):
    """A missing or empty Components section must not silently drop every component from the ladder."""

    TESTS = [trow("REQ-1", E, E, "", "", "")]

    def problems(self, architecture, stages, extra=None):
        files = {"STAGES.md": stages, "ARCHITECTURE.md": architecture, "REQUIREMENTS.md": REQ_OK, E: "x = 1\n"}
        files.update(extra or {})
        root = self.make_repo(files)
        return [p for p in check_project(root)[0] if p.file == "ARCHITECTURE.md"]

    def at4(self):
        return table(row(4, "passed", "file:ARCHITECTURE.md"))

    def test_a_missing_components_section_fires_at_stage_4(self):
        self.assert_mentions(self.problems(doc(tests=self.TESTS), self.at4()), "## Components")

    def test_an_empty_components_table_fires_at_stage_4(self):
        problems = self.problems(doc(comps=[], tests=self.TESTS), self.at4())
        self.assertTrue(any("Components" in m and "no rows" in m for m in messages(problems)), problems)

    def test_a_missing_components_section_fires_at_stage_5(self):
        stages = table(row(5, "passed", "file:OWNERSHIP.md"))
        self.assert_mentions(self.problems(doc(map=[], deps=[]), stages), "## Components")

    def test_a_missing_components_section_is_not_judged_before_stage_4(self):
        self.assertEqual(self.problems(doc(tests=self.TESTS), table()), [])

    def test_a_filled_components_table_passes(self):
        tests = self.TESTS + [trow("Parser", E, E, "", "", "")]
        self.assertFalse(any("Components" in m for m in messages(self.problems(doc(comps=["Parser"], tests=tests),
                                                                                self.at4()))))

    def test_an_open_override_for_stage_4_silences_an_empty_table(self):
        text = doc(tests=self.TESTS) + "\n## Components\n\nOverride: O1\n\n| Component | What it does |\n|---|---|\n"
        extra = {"OVERRIDES.md": overrides_doc(entry(1, stage="4 Verify"))}
        self.assertFalse(any("Components" in m for m in messages(self.problems(text, self.at4(), extra))))


class ArchivedEvidenceRules(GitCase):
    """docs/archive/ holds earlier cycles' records: never a design file, and an archived STAGES file is never evidence."""

    def test_an_archived_file_is_not_the_full_design(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/archive/design.md": "old design\n"})
        r = Row(10, STAGE_NAMES[1], "passed", "file:DECISIONS.md,file:docs/archive/design.md", "-")
        self.assert_mentions(evidence_content_problems(1, "full", root, ls(root), r, None), "design")

    def test_a_design_file_beside_the_archive_still_counts(self):
        root = self.make_repo({"DECISIONS.md": DECISIONS_OK, "docs/design.md": "design\n", "GRILLING.md": GRILL_OK})
        r = Row(10, STAGE_NAMES[1], "passed", EV1 + ",file:docs/design.md", "-")
        self.assertEqual(evidence_content_problems(1, "full", root, ls(root), r, None), [])

    def test_an_archived_stages_file_is_never_evidence(self):
        root = self.make_repo({"docs/archive/STAGES-cycle-1.md": STAGES_OPEN})
        found = check_gates.evidence_item_problems("file", "docs/archive/STAGES-cycle-1.md", root, set(ls(root)))
        self.assertTrue(any("own record" in m for m in found), found)

    def test_another_archived_file_may_be_evidence(self):
        root = self.make_repo({"docs/archive/notes.md": "notes\n"})
        self.assertEqual(check_gates.evidence_item_problems("file", "docs/archive/notes.md", root, set(ls(root))), [])


class BuildCommitRules(GitCase):
    """Stage 3's commit must change something other than the gate's own records."""

    def check(self, files=None, remove=()):
        root = self.make_repo({"README.md": "# p\n", "BUILD-LEDGER.md": LEDGER_OK})
        setup = commit(root, {"STAGES.md": STAGES_OPEN}, "setup")
        later = commit(root, files, "later", remove=remove)
        r = Row(10, STAGE_NAMES[3], "passed", f"commit:{later},file:BUILD-LEDGER.md", "-")
        return evidence_content_problems(3, "small", root, ls(root), r, setup)

    def test_a_commit_that_changes_only_gate_records_fires(self):
        for files in ({"STAGES.md": table(row(0, "passed", "file:REQUIREMENTS.md"))},
                      {"OVERRIDES.md": "# Overrides\n"},
                      {"docs/archive/STAGES-cycle-1.md": STAGES_OPEN},
                      {"STAGES.md": table(cycle=1, extra=("Traits: none",)), "OVERRIDES.md": "# o\n"}):
            with self.subTest(files=sorted(files)):
                self.assert_mentions(self.check(files), "gate's own records")

    def test_an_empty_commit_fires(self):
        self.assert_mentions(self.check(), "gate's own records")

    def test_a_commit_that_also_changes_code_passes(self):
        self.assertEqual(self.check({"STAGES.md": table(extra=("Traits: none",)), "app.py": "x = 1\n"}), [])

    def test_a_commit_that_removes_a_source_file_passes(self):
        root = self.make_repo({"README.md": "# p\n", "BUILD-LEDGER.md": LEDGER_OK, "old.py": "x = 1\n"})
        setup = commit(root, {"STAGES.md": STAGES_OPEN}, "setup")
        later = commit(root, remove=("old.py",), message="remove old code")
        r = Row(10, STAGE_NAMES[3], "passed", f"commit:{later},file:BUILD-LEDGER.md", "-")
        self.assertEqual(evidence_content_problems(3, "small", root, ls(root), r, setup), [])


class CaseSpellingRules(GitCase):
    def test_a_case_only_mismatch_names_the_tracked_spelling(self):
        root = self.make_repo({"Requirements.md": REQ_OK})
        found = check_gates.evidence_item_problems("file", "requirements.md", root, set(ls(root)))
        self.assertTrue(any("tracked as Requirements.md" in m for m in found), found)

    def test_the_tracked_spelling_passes(self):
        root = self.make_repo({"Requirements.md": REQ_OK})
        self.assertEqual(check_gates.evidence_item_problems("file", "Requirements.md", root, set(ls(root))), [])

    def test_a_file_that_is_not_tracked_in_any_spelling_keeps_its_message(self):
        root = self.make_repo()
        write(root, "notes.md", "x\n")
        found = check_gates.evidence_item_problems("file", "notes.md", root, set(ls(root)))
        self.assertTrue(any("not tracked by git" in m for m in found), found)


class DeferredFindingRules(GitCase):
    """Small findings deferred during the build and taken in the final fix wave."""

    def test_a_duplicate_field_label_in_an_override_is_reported_at_its_second_line(self):
        root = self.make_repo()
        text = overrides_doc(entry(1)).replace("- **Status:** open\n", "- **Status:** open\n- **Status:** closed\n")
        problems = override_problems(text, root, parse_stages(STAGES_OPEN))
        second = text.split("\n").index("- **Status:** closed") + 1
        self.assertIn(second, [p.line for p in problems if "twice" in p.message], problems)

    def test_an_override_with_each_label_once_has_no_duplicate_problem(self):
        root = self.make_repo()
        problems = override_problems(overrides_doc(entry(1)), root, parse_stages(STAGES_OPEN))
        self.assertFalse(any("twice" in m for m in messages(problems)), problems)

    def test_a_bare_traits_line_is_a_problem_at_its_line(self):
        text = table(extra=("Traits:",))
        stages = parse_stages(text)
        self.assertIn(line_of(text, "Traits:"), [n for n, m in stages.errors if "Traits" in m], stages.errors)
        self.assertIsNone(stages.traits)

    def test_traits_none_is_still_valid(self):
        stages = parse_stages(table(extra=("Traits: none",)))
        self.assertEqual((stages.traits, stages.errors), (set(), []))

    def merge_repo(self, branch_files):
        """main with a README; a side branch adds `branch_files`; a merge commit (no fast-forward) brings it in."""
        root = self.make_repo({"README.md": "# p\n"})
        main = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        git(root, "switch", "-q", "-c", "side")
        commit(root, branch_files, "side work")
        git(root, "switch", "-q", main)
        commit(root, {"NOTES.md": "n\n"}, "main moves on")
        git(root, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        return root, git(root, "rev-parse", "HEAD")

    def test_a_merge_commit_that_brings_in_source_counts_as_the_hand_change(self):
        root, merge = self.merge_repo({"src/app.py": "x = 1\n"})
        self.assertEqual(check_gates._hand_change_problems(root, merge, 3, "OWNERSHIP.md"), [])

    def test_a_merge_commit_that_brings_in_only_documents_is_not_a_hand_change(self):
        root, merge = self.merge_repo({"docs/a.md": "x\n"})
        self.assertTrue(check_gates._hand_change_problems(root, merge, 3, "OWNERSHIP.md"))

    def test_a_merge_commit_that_brings_in_code_counts_for_stage_3(self):
        root = self.make_repo({"README.md": "# p\n", "BUILD-LEDGER.md": LEDGER_OK})
        setup = commit(root, {"STAGES.md": STAGES_OPEN}, "setup")
        main = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        git(root, "switch", "-q", "-c", "side")
        commit(root, {"app.py": "x = 1\n"}, "side work")
        git(root, "switch", "-q", main)
        commit(root, {"NOTES.md": "n\n"}, "main moves on")
        git(root, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        merge = git(root, "rev-parse", "HEAD")
        r = Row(10, STAGE_NAMES[3], "passed", f"commit:{merge},file:BUILD-LEDGER.md", "-")
        self.assertEqual(evidence_content_problems(3, "small", root, ls(root), r, setup), [])

    def test_clean_lines_blanks_two_comments_in_one_text(self):
        text = "a <!-- one --> b <!-- two --> c\n<!--\nthree\n-->\nkeep\n<!-- four\nfive -->\n"
        self.assertEqual(check_gates.clean_lines(text), ["a  b  c", "", "", "", "keep", "", "", ""])


class OverrideSurvivorRules(GitCase):
    def test_the_last_duplicate_field_wins(self):
        text = "### O1. t\n\n- **Status:** open\n- **Status:** closed\n"
        self.assertEqual(parse_overrides(text)["O1"].status, "closed")

    def test_a_blank_field_is_called_empty(self):
        root = self.make_repo()
        stages = parse_stages(STAGES_OPEN)
        for given in ({"why": ""}, {"closing": ""}):
            problems = override_problems(overrides_doc(entry(1, **given)), root, stages)
            self.assertTrue(any(" is empty" in m for m in messages(problems)), (given, problems))

    def test_an_entry_removed_by_a_merge_is_still_reported_as_vanished(self):
        """git log hides a side branch whose change the merge discarded unless --full-history is given."""
        root = self.make_repo({"OVERRIDES.md": overrides_doc(entry(1))})
        git(root, "switch", "-q", "-c", "side")
        commit(root, {"OVERRIDES.md": overrides_doc(entry(1), entry(2))}, "adds O2")
        git(root, "switch", "-q", "-")
        commit(root, {"other.txt": "x\n"}, "unrelated work")
        git(root, "merge", "-q", "-s", "ours", "-m", "merge that drops O2", "side")
        problems = override_problems(overrides_doc(entry(1)), root, parse_stages(STAGES_OPEN))
        self.assert_mentions(problems, "O2 vanished")


class WiringSurvivorRules(GitCase):
    def test_an_invalid_size_does_not_start_the_attack_count(self):
        """With no usable size the size error is the one reported; the architecture checks wait for it."""
        root = self.make_repo({"ATTACKS.md": attack_doc(1)})
        stages = parse_stages(table(row(0, "passed", "file:ATTACKS.md"), size="huge"))
        self.assertIsNone(stages.size)
        self.assertEqual(check_gates.architecture_problems(root, ls(root), stages, {}), [])

    def test_a_go_live_status_is_read_without_regard_to_case(self):
        for status in ("Proven", "PROVEN", "Not Applicable"):
            self.assertEqual(go_live_problems(gl_rows(("r", "v", "C-SEC-1", status, "ran x: 0 hits")), {"C-SEC-1"}, {}),
                             [], status)

    def test_an_override_line_must_start_its_line(self):
        self.assertFalse(section_override("see Override: O1 for details", {"O1": ov("open", "4 Verify")}, "4"))
        self.assertTrue(section_override("Override: O1", {"O1": ov("open", "4 Verify")}, "4"))

    def test_a_heading_with_extra_words_is_not_the_section(self):
        self.assertIsNone(check_gates._section("## File mapping\n| a |\n", "File map"))
        self.assertIsNotNone(check_gates._section("## File map  \n| a |\n", "File map"))

    def test_the_first_of_a_repeated_ownership_line_wins(self):
        lines = check_gates._ownership_lines("Closed: 2026-01-01\nClosed: 2026-02-02\n")
        self.assertEqual(lines["Closed"], ("2026-01-01", 1))

    def test_a_hand_changed_commit_must_be_a_hash_and_not_a_name(self):
        root = self.make_repo({"src/app.py": "x = 1\n"})
        problems = check_gates._hand_change_problems(root, "HEAD", 3, "OWNERSHIP.md")
        self.assertTrue(any("hexadecimal" in p.message for p in problems), problems)
        self.assertEqual(check_gates._hand_change_problems(root, git(root, "rev-parse", "HEAD"), 3, "OWNERSHIP.md"), [])

    def test_a_trait_with_nothing_to_cover_asks_for_no_go_live_file(self):
        """No checklist items and no attacks means no required ids, so stage 5 need not cite GO-LIVE.md."""
        root = self.make_repo({"checks/checklist.json": "[]"})
        stages = parse_stages(table(row(5, "passed", "file:OWNERSHIP.md")))
        self.assertEqual(check_gates._go_live_stage_problems(root, ls(root), stages, {}, {"web"}), [])

    def test_the_report_lists_ids_in_natural_order(self):
        items = [{"id": "C-SEC-10", "applies_when": ["always"]}, {"id": "C-SEC-2", "applies_when": ["always"]}]
        root = self.make_repo({"STAGES.md": table(size="full"), "checks/checklist.json": json.dumps(items)})
        out, _ = check_gates.go_live_report(root)
        self.assertEqual([line.strip() for line in out[2:]], ["C-SEC-2", "C-SEC-10"])

    def test_an_unreadable_overrides_file_does_not_also_report_vanished_entries(self):
        root = self.make_repo({"STAGES.md": STAGES_OPEN, "OVERRIDES.md": overrides_doc(entry(1))})
        write(root, "OVERRIDES.md", b"\xff\xfe broken")
        problems, _ = check_project(root)
        self.assertTrue(any("not valid UTF-8" in p.message for p in problems), problems)
        self.assertFalse(any("vanished" in p.message for p in problems), problems)

    def test_a_deleted_overrides_file_is_reported_as_vanished_by_the_project_check(self):
        root = self.make_repo({"STAGES.md": STAGES_OPEN, "OVERRIDES.md": overrides_doc(entry(1))})
        (root / "OVERRIDES.md").unlink()
        problems, _ = check_project(root)
        self.assertTrue(any("vanished" in p.message for p in problems), problems)

    def test_problems_come_back_sorted_and_without_repeats(self):
        """A file cited by two stages gives the same UTF-8 problem twice; it is reported once, in file and line order."""
        root = self.make_repo({"REQUIREMENTS.md": REQ_OK, "ATTACKS.md": ATTACKS_OK, "OWNERSHIP.md": b"\xff\xfe"})
        text = table(row(0, "passed", "file:REQUIREMENTS.md,file:ATTACKS.md"), row(5, "passed", "file:OWNERSHIP.md"),
                     row(6, "passed", "file:OWNERSHIP.md"))
        commit(root, {"STAGES.md": text}, "stages")
        problems, _ = check_project(root)
        keys = [(p.file, p.line, p.message) for p in problems]
        self.assertEqual(keys, sorted(set(keys)))
        self.assertEqual(sum(1 for p in problems if p.file == "OWNERSHIP.md" and "not valid UTF-8" in p.message), 1)
        self.assertGreater(len({p.file for p in problems}), 1)

    def test_the_command_refuses_two_arguments_and_a_file(self):
        root = self.make_repo()
        self.assertEqual(run_main([str(root), str(root)])[0], 2)
        code, _, err = run_main([str(root / "README.md")])
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)


class GitHelperSurvivorRules(GitCase):
    def test_a_hand_changed_commit_with_a_non_ascii_source_name_counts_as_source(self):
        """Without core.quotepath=off git prints such a name in quotes with octal escapes, so the extension is missed."""
        root = self.make_repo()
        sha = commit(root, {"café.py": "x = 1\n"}, "hand change")
        self.assertEqual(check_gates._hand_change_problems(root, sha, 3, "OWNERSHIP.md"), [])

    def test_a_tag_object_is_not_a_commit_strictly_after_its_own_commit(self):
        """An annotated tag has its own hash; resolved without ^{commit} it would look like a different commit."""
        root = self.make_repo()
        first = git(root, "rev-parse", "HEAD")
        commit(root, {"a.txt": "x\n"}, "later")
        git(root, "tag", "-a", "-m", "setup", "setup-tag", first)
        tag_object = git(root, "rev-parse", "setup-tag")
        self.assertNotEqual(tag_object, first)
        self.assertFalse(check_gates.commit_is_after(root, first, tag_object))
        self.assertTrue(check_gates.commit_is_after(root, first, git(root, "rev-parse", "HEAD")))
        self.assertEqual(check_gates.resolve_commit(root, tag_object), first)

    def test_a_status_is_read_without_regard_to_case(self):
        self.assertEqual(parse_overrides("### O1. t\n\n- **Status:** Open\n")["O1"].status, "open")

    def test_attack_rows_inside_a_comment_do_not_count(self):
        head = "| ID | Attack | Rung | Drafted by |\n|---|---|---|---|\n"
        text = head + "| ATK-1 | a | 3 | x |\n<!--\n| ATK-2 | b | 3 | x |\n-->\n"
        self.assertEqual(check_gates.attack_ids(text), {"ATK-1"})

    def test_the_ancestor_test_is_true_only_for_exit_code_zero(self):
        """merge-base exits 1 for 'not an ancestor' and 128 for an unknown object; both are False."""
        root = self.make_repo()
        first = git(root, "rev-parse", "HEAD")
        later = commit(root, {"a.txt": "x\n"}, "later")
        self.assertTrue(check_gates.is_ancestor(root, first, later))
        self.assertFalse(check_gates.is_ancestor(root, later, first))
        self.assertFalse(check_gates.is_ancestor(root, "0" * 40, later))


class ManifestSurvivorRules(unittest.TestCase):
    def test_a_wildcard_pin_is_not_a_pinned_version(self):
        self.assertEqual(check_gates._requirements_deps("flask==3.*\n"), [("flask", None)])
        self.assertEqual(check_gates._requirements_deps("flask==3.0.1\n"), [("flask", "3.0.1")])

    def test_an_operator_before_the_double_equals_is_not_a_pin(self):
        self.assertEqual(check_gates._pep508("flask!==1.0"), ("flask", None))

    def test_a_package_json_that_is_not_an_object_is_unreadable(self):
        self.assertIsNone(check_gates._package_json_deps("[1, 2]"))
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "package.json").write_text("[1, 2]", encoding="utf-8")
            deps, unreadable = manifest_dependencies(tmp, ["package.json"])
        self.assertEqual((deps, unreadable), ({}, ["package.json"]))

    def test_attack_ids_ignore_rows_whose_id_is_not_an_attack_id(self):
        text = attack_doc(0, size_rows=[("ATK-1", "a", "3", "x"), ("FOO", "b", "3", "x")])
        self.assertEqual(check_gates.attack_ids(text), {"ATK-1"})

    def test_an_empty_test_table_cell_is_called_empty(self):
        self.assertTrue(check_gates._rung_problem("", Path("."), set()).startswith("empty"))


if __name__ == "__main__":
    unittest.main()
