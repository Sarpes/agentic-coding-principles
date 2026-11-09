"""Tests for init_project.py: what it copies, what it never overwrites, adoption, update and new cycle."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "agentic-principles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_gates  # noqa: E402
import init_project  # noqa: E402
from init_project import InitError  # noqa: E402
from tests.test_check_gates import GitCase, commit, git, messages, write  # noqa: E402

MARK_OPEN, MARK_CLOSE = "<!-- agentic-principles -->", "<!-- /agentic-principles -->"
COMMON = ("DECISIONS.md", "AI-Agents.md", "REQUIREMENTS.md", "ATTACKS.md", "GLOSSARY.md", "BUILD-LEDGER.md",
          "STAGES.md", "ARCHITECTURE.md", "OWNERSHIP.md")
CHECKS = ("checks/check_docs.py", "checks/check_gates.py", "checks/checklist.json")
WORKFLOW = ".github/workflows/agentic-checks.yml"
OVERRIDE_ENTRY = """
### O1. Skip the first review

- **Date:** 2026-11-09
- **Stage:** 3 Build
- **What was skipped:** the independent review of the first task
- **Why:** the owner chose to release the prototype first
- **Risk accepted:** a defect may reach users unreviewed
- **How to close:** run the review and record it in BUILD-LEDGER.md
- **Status:** open
- **Closing evidence:** -
- **Re-confirmed for release:** -
"""


def run_main(*args):
    """(exit code, stdout, stderr) of init_project.main."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = init_project.main(list(args))
    return code, out.getvalue(), err.getvalue()


def stage_status(root, n):
    return check_gates.parse_stages((Path(root) / "STAGES.md").read_text(encoding="utf-8")).rows[n].status


class InitCase(GitCase):
    def make_project(self, size="small", method="normal", files=None, **kwargs):
        root = self.make_repo(files)
        report = init_project.init(root, size, method, **kwargs)
        return root, report

    def commit_report(self, root, report, message="set up the process"):
        for name in report.created:
            git(root, "add", "--", name)
        git(root, "commit", "-q", "-m", message)
        return git(root, "rev-parse", "HEAD")

    def gate(self, root):
        return check_gates.check_project(root)[0]


class TestInit(InitCase):
    def test_fresh_small_init_passes_the_gate(self):
        root, _ = self.make_project("small")
        self.assertEqual(self.gate(root), [])

    def test_fresh_full_init_passes_the_gate(self):
        root, _ = self.make_project("full", "sub-agent")
        self.assertEqual(self.gate(root), [])

    def test_size_and_method_carry_the_arguments(self):
        root, _ = self.make_project("full", "sub-agent")
        stages = check_gates.parse_stages((root / "STAGES.md").read_text(encoding="utf-8"))
        self.assertEqual((stages.size, stages.method), ("full", "sub-agent"))
        self.assertEqual(stages.errors, [])

    def test_other_size_and_method_are_written_too(self):
        root, _ = self.make_project("small", "normal")
        stages = check_gates.parse_stages((root / "STAGES.md").read_text(encoding="utf-8"))
        self.assertEqual((stages.size, stages.method), ("small", "normal"))

    def test_every_common_file_is_copied_and_listed_as_created(self):
        root, report = self.make_project("small")
        for name in COMMON + CHECKS + (WORKFLOW,):
            self.assertTrue((root / name).is_file(), name)
            self.assertIn(name, report.created)
        self.assertEqual(report.kept, [])

    def test_full_adds_overrides_and_go_live(self):
        root, report = self.make_project("full")
        for name in ("OVERRIDES.md", "GO-LIVE.md"):
            self.assertTrue((root / name).is_file(), name)
            self.assertIn(name, report.created)

    def test_small_creates_no_overrides_or_go_live(self):
        root, report = self.make_project("small")
        for name in ("OVERRIDES.md", "GO-LIVE.md"):
            self.assertFalse((root / name).exists(), name)
            self.assertNotIn(name, report.created)
        self.assertEqual(self.gate(root), [])

    def test_existing_decisions_keeps_its_bytes_and_is_listed_as_kept(self):
        root = self.make_repo()
        original = "# My decisions\r\n\r\nkeep \xe9 these bytes\r\n".encode("utf-8")
        (root / "DECISIONS.md").write_bytes(original)
        report = init_project.init(root, "small", "normal")
        self.assertEqual((root / "DECISIONS.md").read_bytes(), original)
        self.assertIn("DECISIONS.md", report.kept)
        self.assertNotIn("DECISIONS.md", report.created)

    def test_existing_stages_file_is_never_rewritten(self):
        root = self.make_repo()
        original = b"Size: full\nMethod: sub-agent\n"
        (root / "STAGES.md").write_bytes(original)
        report = init_project.init(root, "small", "normal")
        self.assertEqual((root / "STAGES.md").read_bytes(), original)
        self.assertIn("STAGES.md", report.kept)

    def test_second_init_creates_nothing(self):
        root, _ = self.make_project("full")
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
        report = init_project.init(root, "full", "normal")
        after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(report.created, [])
        self.assertEqual(before, after)
        self.assertIn("DECISIONS.md", report.kept)

    def test_checklist_is_copied_byte_for_byte(self):
        root, _ = self.make_project("small")
        self.assertEqual((root / "checks" / "checklist.json").read_bytes(),
                         (ROOT / "checklist" / "checklist.json").read_bytes())

    def test_copied_scripts_are_the_repository_scripts(self):
        root, _ = self.make_project("small")
        self.assertEqual((root / "checks" / "check_gates.py").read_bytes(), (SCRIPTS / "check_gates.py").read_bytes())
        self.assertEqual((root / "checks" / "check_docs.py").read_bytes(),
                         (ROOT / "checks" / "check_docs.py").read_bytes())

    def test_init_does_not_run_git_in_the_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = init_project.init(tmp, "small", "normal")
            self.assertFalse((Path(tmp) / ".git").exists())
            self.assertIn("STAGES.md", report.created)

    def test_init_makes_no_commit(self):
        root, _ = self.make_project("small")
        self.assertEqual(git(root, "rev-list", "--count", "HEAD"), "1")

    def test_bad_size_is_refused_and_writes_nothing(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.init(root, "huge", "normal")
        self.assertFalse((root / "STAGES.md").exists())

    def test_bad_method_is_refused(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.init(root, "small", "pair")

    def test_missing_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InitError):
                init_project.init(Path(tmp) / "nowhere", "small", "normal")

    def test_a_file_in_place_of_a_folder_is_refused(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.init(root / "README.md", "small", "normal")

    def test_a_changed_stages_template_layout_is_refused_and_writes_nothing(self):
        root = self.make_repo()
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "templates"
            shutil.copytree(ROOT / "templates", copy)
            text = (copy / "STAGES.md").read_text(encoding="utf-8").replace("\nSize: small\n", "\nSize: any\n")
            (copy / "STAGES.md").write_text(text, encoding="utf-8")
            with mock.patch.object(init_project, "TEMPLATES", copy):
                with self.assertRaises(InitError):
                    init_project.init(root, "small", "normal")
        self.assertFalse((root / "DECISIONS.md").exists())

    def test_template_files_copy_the_templates_exactly(self):
        root, _ = self.make_project("full")
        for name in ("DECISIONS.md", "ATTACKS.md", "OVERRIDES.md", "GO-LIVE.md", "OWNERSHIP.md"):
            self.assertEqual((root / name).read_bytes(), (ROOT / "templates" / name).read_bytes(), name)


class TestOverridesAfterInit(InitCase):
    def test_a_real_first_override_after_init_is_clean(self):
        root, report = self.make_project("full")
        self.commit_report(root, report)
        self.assertEqual(self.gate(root), [])
        path = root / "OVERRIDES.md"
        path.write_bytes(path.read_bytes() + OVERRIDE_ENTRY.encode("utf-8"))
        commit(root, {"OVERRIDES.md": path.read_bytes()}, "log the first override")
        problems = self.gate(root)
        self.assertEqual(problems, [], messages(problems))

    def test_no_phantom_override_exists_before_the_first_entry(self):
        root, _ = self.make_project("full")
        overrides = check_gates.parse_overrides((root / "OVERRIDES.md").read_text(encoding="utf-8"))
        self.assertEqual(overrides, {})

    def test_deleting_the_entry_afterwards_is_still_caught(self):
        root, report = self.make_project("full")
        self.commit_report(root, report)
        text = (root / "OVERRIDES.md").read_bytes() + OVERRIDE_ENTRY.encode("utf-8")
        commit(root, {"OVERRIDES.md": text}, "log the first override")
        commit(root, {"OVERRIDES.md": (ROOT / "templates" / "OVERRIDES.md").read_bytes()}, "drop it")
        self.assertTrue(any("vanished" in m for m in messages(self.gate(root))))


class TestClaudeBlock(InitCase):
    def test_block_for_empty_text_is_the_marked_block(self):
        text = init_project.claude_block("")
        self.assertEqual(text.count(MARK_OPEN), 1)
        self.assertEqual(text.count(MARK_CLOSE), 1)
        self.assertLess(text.index(MARK_OPEN), text.index(MARK_CLOSE))

    def test_block_names_the_skill_the_load_the_stage_rule_and_the_overlap_table(self):
        text = init_project.claude_block("")
        for needle in ("agentic-principles skill", "every session", "STAGES.md", "next step", "overlap table"):
            self.assertIn(needle, text)

    def test_existing_text_is_kept_and_the_block_is_added(self):
        existing = "# Project rules\n\n- Never edit the vendor folder.\n"
        text = init_project.claude_block(existing)
        self.assertTrue(text.startswith(existing.rstrip("\n")))
        self.assertIn(MARK_OPEN, text)

    def test_running_twice_adds_the_block_once(self):
        once = init_project.claude_block("# Rules\n")
        twice = init_project.claude_block(once)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count(MARK_OPEN), 1)

    def test_a_stale_block_is_refreshed_and_the_text_around_it_is_kept(self):
        stale = f"before\n\n{MARK_OPEN}\nold words\n{MARK_CLOSE}\n\nafter\n"
        text = init_project.claude_block(stale)
        self.assertNotIn("old words", text)
        self.assertTrue(text.startswith("before\n"))
        self.assertTrue(text.rstrip().endswith("after"))
        self.assertEqual(text.count(MARK_OPEN), 1)

    def test_an_opening_marker_without_a_closing_one_is_refused(self):
        with self.assertRaises(InitError):
            init_project.claude_block(f"text\n{MARK_OPEN}\nno end\n")

    def test_a_closing_marker_without_an_opening_one_is_refused(self):
        with self.assertRaises(InitError):
            init_project.claude_block(f"text\n{MARK_CLOSE}\n")

    def test_two_blocks_are_refused_not_a_third_added(self):
        two = f"{MARK_OPEN}\na\n{MARK_CLOSE}\n\n{MARK_OPEN}\nb\n{MARK_CLOSE}\n"
        with self.assertRaises(InitError):
            init_project.claude_block(two)

    def test_markers_in_the_wrong_order_are_refused(self):
        with self.assertRaises(InitError):
            init_project.claude_block(f"{MARK_CLOSE}\ntext\n{MARK_OPEN}\n")

    def test_a_claude_md_that_is_not_utf8_is_refused_and_left_alone(self):
        root = self.make_repo()
        (root / "CLAUDE.md").write_bytes(b"caf\xe9 rules\n")
        with self.assertRaises(InitError):
            init_project.init(root, "small", "normal")
        self.assertEqual((root / "CLAUDE.md").read_bytes(), b"caf\xe9 rules\n")
        self.assertFalse((root / "STAGES.md").exists())

    def test_windows_line_endings_stay_windows_line_endings(self):
        text = init_project.claude_block("# Rules\r\n\r\nline\r\n")
        self.assertNotIn("\n", text.replace("\r\n", ""))

    def test_init_creates_claude_md_with_the_block(self):
        root, report = self.make_project("small")
        self.assertIn(MARK_OPEN, (root / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("CLAUDE.md", report.created)

    def test_init_keeps_existing_claude_md_text(self):
        root = self.make_repo({"README.md": "x\n", "CLAUDE.md": "# Mine\n\n- keep this line\n"})
        init_project.init(root, "small", "normal")
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("- keep this line", text)
        self.assertEqual(text.count(MARK_OPEN), 1)

    def test_second_init_leaves_claude_md_untouched(self):
        root, _ = self.make_project("small")
        before = (root / "CLAUDE.md").read_bytes()
        report = init_project.init(root, "small", "normal")
        self.assertEqual((root / "CLAUDE.md").read_bytes(), before)
        self.assertNotIn("CLAUDE.md", report.created)

    def test_the_dot_claude_layout_is_used_when_it_is_the_one_present(self):
        root = self.make_repo({"README.md": "x\n", ".claude/CLAUDE.md": "# Layout\n"})
        init_project.init(root, "small", "normal")
        self.assertFalse((root / "CLAUDE.md").exists())
        self.assertIn(MARK_OPEN, (root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_broken_markers_stop_init_before_anything_is_written(self):
        root = self.make_repo({"README.md": "x\n", "CLAUDE.md": f"{MARK_OPEN}\nunfinished\n"})
        with self.assertRaises(InitError):
            init_project.init(root, "small", "normal")
        self.assertFalse((root / "STAGES.md").exists())


class TestAdopt(InitCase):
    def test_adopt_at_4_writes_the_line_and_marks_stages_0_to_3(self):
        root, _ = self.make_project("small", adopt_at=4)
        text = (root / "STAGES.md").read_text(encoding="utf-8")
        stages = check_gates.parse_stages(text)
        self.assertEqual(stages.adopted_at, 4)
        self.assertEqual([stages.rows[n].status for n in range(8)],
                         ["adopted"] * 4 + ["open"] * 4)
        self.assertEqual(stages.errors, [])

    def test_without_adopt_at_there_is_no_adoption(self):
        root, _ = self.make_project("small")
        stages = check_gates.parse_stages((root / "STAGES.md").read_text(encoding="utf-8"))
        self.assertIsNone(stages.adopted_at)
        self.assertEqual({r.status for r in stages.rows.values()}, {"open"})

    def test_adoption_of_a_project_with_source_passes_the_gate_after_commit(self):
        root = self.make_repo({"README.md": "x\n", "app.py": "print(1)\n"})
        report = init_project.init(root, "small", "normal", adopt_at=4)
        self.commit_report(root, report)
        problems = self.gate(root)
        self.assertEqual(problems, [], messages(problems))

    def test_adoption_of_a_project_without_source_is_caught_by_the_gate(self):
        root, report = self.make_project("small", adopt_at=4)
        self.commit_report(root, report)
        self.assertTrue(any("no source files" in m for m in messages(self.gate(root))))

    def test_adopt_at_5_is_allowed(self):
        root, _ = self.make_project("small", adopt_at=5)
        self.assertEqual(stage_status(root, 4), "adopted")
        self.assertEqual(stage_status(root, 5), "open")

    def test_adopt_at_6_is_refused(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.init(root, "small", "normal", adopt_at=6)
        self.assertFalse((root / "STAGES.md").exists())

    def test_adopt_at_9_is_refused(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.init(root, "small", "normal", adopt_at=9)

    def test_adopt_at_0_and_negative_are_refused(self):
        root = self.make_repo()
        for bad in (0, -1):
            with self.assertRaises(InitError):
                init_project.init(root, "small", "normal", adopt_at=bad)

    def test_cli_exit_2_for_9_and_for_6_and_0_for_5(self):
        root = self.make_repo()
        for bad in ("9", "6"):
            code, _, _ = run_main(str(root), "--size", "small", "--method", "normal", "--adopt-at", bad)
            self.assertEqual(code, 2, bad)
        code, _, _ = run_main(str(root), "--size", "small", "--method", "normal", "--adopt-at", "5")
        self.assertEqual(code, 0)

    def test_second_cycle_reads_adopted_at_from_the_new_file(self):
        root = self.make_repo({"README.md": "x\n", "app.py": "print(1)\n"})
        first = init_project.init(root, "small", "normal", adopt_at=2)
        self.commit_report(root, first)
        commit(root, remove=("STAGES.md",), message="archive the first cycle")
        second = init_project.init(root, "small", "normal", adopt_at=4)
        self.assertEqual(second.created, ["STAGES.md"])
        git(root, "add", "--", "STAGES.md")
        git(root, "commit", "-q", "-m", "second cycle setup")
        problems = self.gate(root)
        self.assertEqual(problems, [], messages(problems))


class TestWorkflow(InitCase):
    def text(self, root):
        return (root / WORKFLOW).read_text(encoding="utf-8")

    def test_workflow_fetches_the_full_history(self):
        root, _ = self.make_project("small")
        self.assertIn("fetch-depth: 0", self.text(root))

    def test_workflow_runs_both_checks(self):
        root, _ = self.make_project("small")
        text = self.text(root)
        self.assertIn("python checks/check_docs.py", text)
        self.assertIn("python checks/check_gates.py", text)

    def test_workflow_uses_no_secrets(self):
        root, _ = self.make_project("small")
        self.assertNotIn("secrets.", self.text(root))

    def test_workflow_template_is_the_copied_file(self):
        root, _ = self.make_project("small")
        self.assertEqual((root / WORKFLOW).read_bytes(), (ROOT / "templates" / "agentic-checks.yml").read_bytes())

    def test_an_existing_workflow_is_kept(self):
        root = self.make_repo()
        write(root, WORKFLOW, "name: mine\n")
        report = init_project.init(root, "small", "normal")
        self.assertEqual((root / WORKFLOW).read_text(encoding="utf-8"), "name: mine\n")
        self.assertIn(WORKFLOW, report.kept)


class TestCopiedScripts(InitCase):
    def run_script(self, root, name):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        return subprocess.run([sys.executable, "-I", str(root / "checks" / name), str(root)],
                              capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(root.parent))

    def test_copied_check_gates_runs_from_the_target_alone(self):
        root, _ = self.make_project("small")
        result = self.run_script(root, "check_gates.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_copied_check_docs_runs_from_the_target_alone(self):
        root, _ = self.make_project("small")
        result = self.run_script(root, "check_docs.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_copied_check_gates_still_fires_on_a_broken_stage_file(self):
        root, _ = self.make_project("small")
        text = (root / "STAGES.md").read_text(encoding="utf-8").replace(
            "| 0 Intake | open | - | - |", "| 0 Intake | passed | - | - |")
        (root / "STAGES.md").write_text(text, encoding="utf-8")
        self.assertEqual(self.run_script(root, "check_gates.py").returncode, 1)


class TestWhere(unittest.TestCase):
    def test_where_prints_a_folder_holding_principles_and_checklist(self):
        code, out, _ = run_main("--where")
        self.assertEqual(code, 0)
        folder = Path(out.strip())
        self.assertTrue((folder / "principles").is_dir())
        self.assertTrue((folder / "checklist").is_dir())

    def test_where_is_the_repository_root(self):
        self.assertEqual(init_project.where().resolve(), ROOT.resolve())

    def test_a_folder_without_those_two_is_not_reported_as_the_root(self):
        self.assertFalse((SCRIPTS / "principles").is_dir())
        self.assertNotEqual(init_project.where().resolve(), SCRIPTS.resolve())


class TestUpdateChecks(InitCase):
    def test_update_replaces_the_script_and_keeps_a_backup(self):
        root, _ = self.make_project("small")
        target = root / "checks" / "check_gates.py"
        old = b"# an old copy\n"
        target.write_bytes(old)
        report = init_project.update_checks(root)
        self.assertEqual(target.read_bytes(), (SCRIPTS / "check_gates.py").read_bytes())
        backup = root / "checks" / "check_gates.py.bak"
        self.assertEqual(backup.read_bytes(), old)
        self.assertIn("checks/check_gates.py", report.updated)
        self.assertIn("checks/check_gates.py.bak", report.backups)

    def test_update_of_an_identical_copy_changes_nothing_and_makes_no_backup(self):
        root, _ = self.make_project("small")
        report = init_project.update_checks(root)
        self.assertEqual(report.updated, [])
        self.assertEqual(list(root.glob("checks/*.bak")), [])
        self.assertIn("checks/check_gates.py", report.kept)

    def test_an_existing_backup_is_never_overwritten(self):
        root, _ = self.make_project("small")
        target = root / "checks" / "check_docs.py"
        (root / "checks" / "check_docs.py.bak").write_bytes(b"first backup\n")
        target.write_bytes(b"# changed again\n")
        init_project.update_checks(root)
        self.assertEqual((root / "checks" / "check_docs.py.bak").read_bytes(), b"first backup\n")
        self.assertEqual((root / "checks" / "check_docs.py.bak2").read_bytes(), b"# changed again\n")

    def test_a_missing_check_file_is_created(self):
        root, _ = self.make_project("small")
        (root / "checks" / "checklist.json").unlink()
        report = init_project.update_checks(root)
        self.assertTrue((root / "checks" / "checklist.json").is_file())
        self.assertIn("checks/checklist.json", report.created)

    def test_update_leaves_the_owners_documents_alone(self):
        root, _ = self.make_project("small")
        (root / "DECISIONS.md").write_bytes(b"# mine\n")
        (root / "STAGES.md").write_bytes(b"mine\n")
        init_project.update_checks(root)
        self.assertEqual((root / "DECISIONS.md").read_bytes(), b"# mine\n")
        self.assertEqual((root / "STAGES.md").read_bytes(), b"mine\n")

    def test_update_on_a_missing_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InitError):
                init_project.update_checks(Path(tmp) / "nowhere")

    def test_cli_update_checks(self):
        root, _ = self.make_project("small")
        (root / "checks" / "check_gates.py").write_bytes(b"# old\n")
        code, _, _ = run_main("--update-checks", str(root))
        self.assertEqual(code, 0)
        self.assertEqual((root / "checks" / "check_gates.py.bak").read_bytes(), b"# old\n")

    def test_cli_update_checks_on_a_missing_folder_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run_main("--update-checks", str(Path(tmp) / "nowhere"))
        self.assertEqual(code, 2)


class TestNewCycle(InitCase):
    def test_new_cycle_archives_the_old_file_and_loses_nothing(self):
        root, _ = self.make_project("full", "sub-agent")
        old = (root / "STAGES.md").read_bytes()
        report = init_project.new_cycle(root)
        archived = sorted((root / "docs" / "archive").glob("STAGES*.md"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), old)
        self.assertIn("cycle", archived[0].name)
        self.assertIn("docs/archive/" + archived[0].name, report.created)

    def test_the_fresh_file_is_all_open_with_the_same_size_and_method(self):
        root, _ = self.make_project("full", "sub-agent", adopt_at=3)
        init_project.new_cycle(root)
        stages = check_gates.parse_stages((root / "STAGES.md").read_text(encoding="utf-8"))
        self.assertEqual((stages.size, stages.method), ("full", "sub-agent"))
        self.assertEqual({r.status for r in stages.rows.values()}, {"open"})
        self.assertIsNone(stages.adopted_at)
        self.assertEqual(stages.errors, [])

    def test_a_second_new_cycle_does_not_overwrite_the_first_archive(self):
        root, _ = self.make_project("small")
        init_project.new_cycle(root)
        (root / "STAGES.md").write_bytes((root / "STAGES.md").read_bytes() + b"\n")
        init_project.new_cycle(root)
        archived = sorted((root / "docs" / "archive").glob("STAGES*.md"))
        self.assertEqual(len(archived), 2)
        self.assertNotEqual(archived[0].read_bytes(), archived[1].read_bytes())

    def test_declared_traits_carry_over(self):
        root, _ = self.make_project("full")
        path = root / "STAGES.md"
        text = path.read_text(encoding="utf-8").replace("\nMethod: normal\n", "\nMethod: normal\nTraits: personal-data\n", 1)
        path.write_text(text, encoding="utf-8")
        init_project.new_cycle(root)
        stages = check_gates.parse_stages((root / "STAGES.md").read_text(encoding="utf-8"))
        self.assertEqual(stages.traits, {"personal-data"})

    def test_new_cycle_without_a_stages_file_is_refused(self):
        root = self.make_repo()
        with self.assertRaises(InitError):
            init_project.new_cycle(root)
        self.assertFalse((root / "docs").exists())

    def test_new_cycle_with_an_unreadable_stages_file_is_refused_and_keeps_it(self):
        root = self.make_repo()
        write(root, "STAGES.md", "nothing useful here\n")
        with self.assertRaises(InitError):
            init_project.new_cycle(root)
        self.assertEqual((root / "STAGES.md").read_bytes(), b"nothing useful here\n")
        self.assertFalse((root / "docs").exists())

    def test_the_report_tells_the_owner_to_commit_in_two_steps(self):
        root, _ = self.make_project("small")
        report = init_project.new_cycle(root)
        self.assertTrue(any("two commits" in note for note in report.notes), report.notes)

    def test_after_the_two_step_commit_the_gate_is_clean(self):
        root, report = self.make_project("small")
        self.commit_report(root, report)
        made = init_project.new_cycle(root)
        archive = [n for n in made.created if n.startswith("docs/archive/")][0]
        git(root, "add", "--", archive)
        git(root, "rm", "-q", "--cached", "--", "STAGES.md")
        git(root, "commit", "-q", "-m", "archive the first cycle")
        git(root, "add", "--", "STAGES.md")
        git(root, "commit", "-q", "-m", "second cycle setup")
        problems = self.gate(root)
        self.assertEqual(problems, [], messages(problems))

    def test_cli_new_cycle(self):
        root, _ = self.make_project("small")
        code, out, _ = run_main("--new-cycle", str(root))
        self.assertEqual(code, 0)
        self.assertTrue(list((root / "docs" / "archive").glob("STAGES*.md")))
        self.assertIn("two commits", out)

    def test_cli_new_cycle_on_a_missing_folder_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run_main("--new-cycle", str(Path(tmp) / "nowhere"))
        self.assertEqual(code, 2)


class TestCli(InitCase):
    def test_cli_init_creates_the_files_and_prints_them(self):
        root = self.make_repo()
        code, out, _ = run_main(str(root), "--size", "full", "--method", "sub-agent")
        self.assertEqual(code, 0)
        self.assertTrue((root / "OVERRIDES.md").is_file())
        self.assertIn("STAGES.md", out)

    def test_cli_bad_size_exits_2(self):
        root = self.make_repo()
        self.assertEqual(run_main(str(root), "--size", "huge", "--method", "normal")[0], 2)

    def test_cli_bad_method_exits_2(self):
        root = self.make_repo()
        self.assertEqual(run_main(str(root), "--size", "small", "--method", "pair")[0], 2)

    def test_cli_missing_folder_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run_main(str(Path(tmp) / "nowhere"), "--size", "small", "--method", "normal")
        self.assertEqual(code, 2)

    def test_cli_without_size_or_method_exits_2(self):
        root = self.make_repo()
        self.assertEqual(run_main(str(root))[0], 2)
        self.assertEqual(run_main(str(root), "--size", "small")[0], 2)

    def test_cli_with_no_arguments_exits_2(self):
        self.assertEqual(run_main()[0], 2)

    def test_cli_modes_do_not_mix(self):
        root = self.make_repo()
        self.assertEqual(run_main("--where", str(root))[0], 2)
        self.assertEqual(run_main("--update-checks", str(root), "--new-cycle", str(root))[0], 2)
        self.assertEqual(run_main("--new-cycle", str(root), "--size", "small")[0], 2)
        self.assertFalse((root / "STAGES.md").exists())

    def test_cli_broken_claude_markers_exit_2(self):
        root = self.make_repo({"README.md": "x\n", "CLAUDE.md": f"{MARK_OPEN}\nunfinished\n"})
        self.assertEqual(run_main(str(root), "--size", "small", "--method", "normal")[0], 2)


if __name__ == "__main__":
    unittest.main()
