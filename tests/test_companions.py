"""Tests for the companion mapping (companions.json) and its checker (check_companions.py).

Temporary folders stand in for the plugin cache; the real home folder is never read.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "agentic-principles"
sys.path.insert(0, str(SKILL / "scripts"))

import check_companions  # noqa: E402
from check_companions import (  # noqa: E402
    installed,
    load,
    main,
    mapping_problems,
    missing,
    report,
)


def row(**over):
    base = {
        "stages": [1],
        "capability": "Finding out",
        "primary": "p:s",
        "also": [],
        "fallback": "ask questions",
        "kind": "skill",
        "requires": [],
    }
    base.update(over)
    return base


class TestRealMapping(unittest.TestCase):
    def setUp(self):
        self.rows = load(SKILL / "companions.json")

    def test_real_file_has_the_thirty_design_rows(self):
        self.assertEqual(len(self.rows), 30)

    def test_real_file_has_no_problems(self):
        self.assertEqual(mapping_problems(self.rows), [])

    def test_grilling_runs_at_intake_and_design_on_every_project(self):
        """The owner's ruling (2026-11-10): grill-me runs in every project, Small or Full, at stage 0 and stage 1."""
        rows = [r for r in self.rows if r["primary"] == "mattpocock-skills:grilling"]
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(sorted(rows[0]["stages"]), [0, 1])
        self.assertNotIn("Full", rows[0]["capability"])

    def test_every_stage_zero_to_seven_is_covered(self):
        covered = {s for r in self.rows for s in r["stages"]}
        self.assertEqual(covered, set(range(8)))

    def test_builtin_and_local_rows_are_the_expected_ones(self):
        by_kind = {}
        for r in self.rows:
            by_kind.setdefault(r["kind"], set()).add(r["primary"])
        self.assertEqual(by_kind["builtin"], {"run", "security-review"})
        self.assertEqual(by_kind["local"], {"repo-kickoff", "templates/PULL_REQUEST_TEMPLATE.md"})

    def test_workflow_requirement_is_recorded(self):
        needs = {r["primary"] for r in self.rows if "Workflow" in r["requires"]}
        self.assertEqual(
            needs,
            {
                "spec-to-code-compliance:spec-to-code-compliance",
                "audit-context-building:audit-context-building",
                "/insecure-defaults:audit",
            },
        )


class TestMappingProblems(unittest.TestCase):
    def test_a_good_row_has_no_problems(self):
        self.assertEqual(mapping_problems([row()]), [])

    def test_blank_fallback_fires(self):
        self.assertNotEqual(mapping_problems([row(fallback="  ")]), [])

    def test_filled_fallback_does_not_fire(self):
        self.assertEqual(mapping_problems([row(fallback="x")]), [])

    def test_repeated_capability_fires(self):
        self.assertNotEqual(mapping_problems([row(), row(primary="q:t")]), [])

    def test_different_capabilities_do_not_fire(self):
        self.assertEqual(mapping_problems([row(), row(capability="Other", primary="q:t")]), [])

    def test_stage_above_seven_fires(self):
        self.assertNotEqual(mapping_problems([row(stages=[8])]), [])

    def test_stage_seven_does_not_fire(self):
        self.assertEqual(mapping_problems([row(stages=[7])]), [])

    def test_unknown_kind_fires(self):
        self.assertNotEqual(mapping_problems([row(kind="plugin")]), [])

    def test_skill_without_colon_fires(self):
        self.assertNotEqual(mapping_problems([row(primary="nocolon")]), [])

    def test_builtin_without_colon_does_not_fire(self):
        self.assertEqual(mapping_problems([row(primary="run", kind="builtin")]), [])

    def test_command_without_slash_fires(self):
        self.assertNotEqual(mapping_problems([row(primary="p:c", kind="command")]), [])

    def test_command_without_colon_fires(self):
        self.assertNotEqual(mapping_problems([row(primary="/pc", kind="command")]), [])

    def test_well_formed_command_does_not_fire(self):
        self.assertEqual(mapping_problems([row(primary="/p:c", kind="command")]), [])


class Machine:
    """A temporary Claude folder with one plugin p from marketplace m."""

    def __init__(self, enabled=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.claude = Path(self.tmp.name)
        self.plugins = self.claude / "plugins"
        self.settings = self.claude / "settings.json"
        self.settings.write_text(json.dumps({"enabledPlugins": {"p@m": enabled}}), encoding="utf-8")

    def put(self, rel, text="x"):
        path = self.plugins / "cache" / "m" / "p" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def skill(self, version, name, folder="skills/engineering/s"):
        self.put(f"{version}/{folder}/SKILL.md", f"---\nname: {name}\ndescription: d\n---\nbody\n")

    def close(self):
        self.tmp.cleanup()


class TestInstalled(unittest.TestCase):
    def setUp(self):
        self.m = Machine()
        self.addCleanup(self.m.close)

    def test_nested_skill_name_comes_from_frontmatter(self):
        self.m.skill("1.0", "s")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:s"})

    def test_folder_name_is_not_used_when_frontmatter_differs(self):
        self.m.skill("1.0", "other", folder="skills/engineering/s")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:other"})

    def test_command_is_stored_with_slash(self):
        self.m.put("1.0/commands/c.md")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"/p:c"})

    def test_agent_is_stored_without_slash(self):
        self.m.put("1.0/agents/a.md")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:a"})

    def test_markdown_outside_agents_and_commands_is_ignored(self):
        self.m.put("1.0/docs/notes.md")
        self.assertEqual(installed(self.m.plugins, self.m.settings), set())

    def test_skill_file_without_name_is_ignored(self):
        self.m.put("1.0/skills/s/SKILL.md", "no frontmatter here\n")
        self.assertEqual(installed(self.m.plugins, self.m.settings), set())

    def test_all_three_kinds_together(self):
        self.m.skill("1.0", "s")
        self.m.put("1.0/commands/c.md")
        self.m.put("1.0/agents/a.md")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:s", "/p:c", "p:a"})

    def test_temp_git_folder_is_ignored(self):
        self.m.skill("1.0", "s")
        self.m.skill("temp_git_99", "junk")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:s"})

    def test_only_newest_version_counts(self):
        self.m.skill("1.2", "old", folder="skills/old")
        self.m.skill("1.10", "new", folder="skills/new")
        self.assertEqual(installed(self.m.plugins, self.m.settings), {"p:new"})

    def test_missing_settings_gives_empty_set(self):
        self.m.skill("1.0", "s")
        self.m.settings.unlink()
        self.assertEqual(installed(self.m.plugins, self.m.settings), set())


class TestDisabled(unittest.TestCase):
    def test_disabled_plugin_gives_empty_set(self):
        m = Machine(enabled=False)
        self.addCleanup(m.close)
        m.skill("1.0", "s")
        self.assertEqual(installed(m.plugins, m.settings), set())

    def test_plugin_absent_from_enabled_map_gives_empty_set(self):
        m = Machine()
        self.addCleanup(m.close)
        m.skill("1.0", "s")
        m.settings.write_text(json.dumps({"enabledPlugins": {"q@m": True}}), encoding="utf-8")
        self.assertEqual(installed(m.plugins, m.settings), set())


class TestMissing(unittest.TestCase):
    def test_absent_skill_is_reported(self):
        self.assertEqual(missing([row()], set()), ["p:s"])

    def test_present_skill_is_not_reported(self):
        self.assertEqual(missing([row()], {"p:s"}), [])

    def test_builtin_and_local_rows_are_ignored(self):
        rows = [
            row(capability="a", primary="run", kind="builtin"),
            row(capability="b", primary="repo-kickoff", kind="local"),
        ]
        self.assertEqual(missing(rows, set()), [])

    def test_plugin_name_in_also_of_a_builtin_row_is_checked(self):
        r = row(primary="run", kind="builtin", also=["example-skills:webapp-testing"])
        self.assertEqual(missing([r], set()), ["example-skills:webapp-testing"])

    def test_plugin_name_in_also_of_a_local_row_present_is_not_reported(self):
        r = row(primary="repo-kickoff", kind="local", also=["q:t"])
        self.assertEqual(missing([r], {"q:t"}), [])

    def test_plain_word_in_also_of_a_builtin_row_is_not_looked_up(self):
        r = row(primary="run", kind="builtin", also=["plainword"])
        self.assertEqual(missing([r], set()), [])

    def test_every_also_name_is_checked(self):
        r = row(also=["q:t", "r:u"])
        self.assertEqual(missing([r], {"p:s", "r:u"}), ["q:t"])

    def test_a_name_used_twice_is_reported_once(self):
        rows = [row(), row(capability="Other")]
        self.assertEqual(missing(rows, set()), ["p:s"])


class TestReport(unittest.TestCase):
    def test_requires_is_printed_beside_a_missing_name(self):
        r = row(primary="/p:c", kind="command", requires=["Workflow"])
        text = "\n".join(report([r], set()))
        self.assertIn("/p:c", text)
        self.assertIn("Workflow", text)

    def test_requires_is_printed_for_an_installed_name_too(self):
        r = row(requires=["Workflow"])
        text = "\n".join(report([r], {"p:s"}))
        self.assertIn("Workflow", text)

    def test_missing_line_says_to_confirm_against_the_session_list(self):
        text = " ".join(report([row()], set()))
        self.assertIn("plugin cache", text)
        self.assertIn("session", text)
        self.assertNotIn("fallback in companions.json applies", text)

    def test_nothing_missing_and_no_requires_prints_a_clean_line(self):
        lines = report([row()], {"p:s"})
        self.assertEqual(len(lines), 1)
        self.assertNotIn("p:s", lines[0])


class TestMain(unittest.TestCase):
    def test_main_exits_zero_and_prints_missing(self):
        m = Machine()
        self.addCleanup(m.close)
        rows_file = SKILL / "companions.json"
        self.assertTrue(rows_file.is_file())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(m.claude)])
        self.assertEqual(code, 0)
        self.assertIn("superpowers:brainstorming", out.getvalue())


class TestMainNeverRaises(unittest.TestCase):
    def test_malformed_companions_file_prints_and_exits_zero(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad = Path(tmp.name) / "companions.json"
        bad.write_text("{not json", encoding="utf-8")
        out = io.StringIO()
        with mock.patch.object(check_companions, "COMPANIONS", bad), contextlib.redirect_stdout(out):
            code = main([tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("companions.json", out.getvalue())

    def test_list_valued_enabled_plugins_gives_empty_set(self):
        m = Machine()
        self.addCleanup(m.close)
        m.skill("1.0", "s")
        m.settings.write_text(json.dumps({"enabledPlugins": ["p@m"]}), encoding="utf-8")
        self.assertEqual(installed(m.plugins, m.settings), set())

    def test_list_valued_enabled_plugins_does_not_stop_main(self):
        m = Machine()
        self.addCleanup(m.close)
        m.settings.write_text(json.dumps({"enabledPlugins": ["p@m"]}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(m.claude)])
        self.assertEqual(code, 0)
        self.assertIn("MISSING", out.getvalue())

    def test_valid_companions_file_still_reports(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        good = Path(tmp.name) / "companions.json"
        good.write_text(json.dumps([row()]), encoding="utf-8")
        out = io.StringIO()
        with mock.patch.object(check_companions, "COMPANIONS", good), contextlib.redirect_stdout(out):
            code = main([tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("p:s", out.getvalue())


if __name__ == "__main__":
    unittest.main()
