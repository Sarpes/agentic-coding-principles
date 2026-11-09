"""Tests for the agentic-principles skill files and the plugin manifests.

A skill is only instructions, so these tests check what can be checked by reading the files: the frontmatter,
the size limit of the router, the shape of each stage file, that every companion a file names is one the mapping
holds for that stage, that the description stays clear of the repository-starting skill's trigger words, and that
the manifests point at the skill. Whether an agent obeys the instructions is tested with pressure scenarios, not here.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "agentic-principles"
SKILL = SKILL_DIR / "SKILL.md"
STAGES = SKILL_DIR / "stages"
COMPANIONS = SKILL_DIR / "companions.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
VERSION = "0.2.0"
HEADINGS = ("## Purpose", "## Do", "## Companions", "## Gate", "## Small")
STAGE_FILES = ("00-intake.md", "01-design.md", "02-plan.md", "03-build.md", "04-verify.md", "05-ship.md",
               "06-own.md", "07-retro.md")
# The trigger phrases of the live repository-starting skill; this skill's description must use none of them,
# so a plain request to start a task or open a pull request does not load it.
KICKOFF_TRIGGERS = ("new project", "set up the repo", "yeni proje", "repo kur", "readme yaz", "requirements",
                    "gitignore", "repoyu denetle", "start a task", "open a pr", "pr aç", "undo a commit", "git undo",
                    "geri al", "commit'i geri al", "i pushed a secret")
# A companion named in backticks: plugin:skill, plugin:agent or /plugin:command.
NAMED = re.compile(r"`(/?[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9-]*)`")
PRONOUNS = re.compile(r"\b(he|she|him|her|his|hers|himself|herself)\b", re.IGNORECASE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return {}


def description_trigger_hits(description: str) -> list[str]:
    """Stub until the fix commit: the trigger phrases found in a description."""
    return []


def section(text: str, heading: str) -> list[str]:
    """The lines under a level-two heading, up to the next one."""
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def companions() -> list[dict]:
    return json.loads(read(COMPANIONS))


def names_for_stage(stage: int) -> set[str]:
    out = set()
    for row in companions():
        if stage in row["stages"]:
            out.add(row["primary"])
            out.update(row.get("also", []))
    return out


def all_names() -> set[str]:
    out = set()
    for row in companions():
        out.add(row["primary"])
        out.update(row.get("also", []))
    return out


def named_companions(text: str) -> set[str]:
    return set(NAMED.findall(text))


class FrontmatterTest(unittest.TestCase):
    def test_name(self):
        self.assertEqual(frontmatter(read(SKILL)).get("name"), "agentic-principles")

    def test_description_starts_use_when_and_fits(self):
        desc = frontmatter(read(SKILL)).get("description", "")
        self.assertTrue(desc.startswith("Use when"), desc[:40])
        self.assertLessEqual(len(desc), 1024)

    def test_description_avoids_repo_kickoff_triggers(self):
        self.assertEqual(description_trigger_hits(frontmatter(read(SKILL)).get("description", "")), [])

    def test_trigger_check_can_fire(self):
        self.assertEqual(description_trigger_hits("Use when asked to Start a Task or to open a PR"),
                         ["start a task", "open a pr"])

    def test_trigger_check_leaves_a_clean_description_alone(self):
        self.assertEqual(description_trigger_hits("Use when a project runs under staged gates"), [])


class RouterTest(unittest.TestCase):
    def test_at_most_150_lines(self):
        self.assertLessEqual(len(read(SKILL).splitlines()), 150)

    def test_router_names_the_scripts(self):
        text = read(SKILL)
        for needle in ("check_gates.py", "init_project.py --where", "check_companions.py", "STAGES.md",
                       "OVERRIDES.md", "GLOSSARY.md"):
            self.assertIn(needle, text)

    def test_router_states_the_trust_limit(self):
        self.assertIn("trust limit", read(SKILL).lower())

    def test_router_has_the_repo_kickoff_overlap_row(self):
        rows = [line for line in read(SKILL).splitlines() if line.startswith("|") and "repo-kickoff" in line]
        self.assertTrue(rows, "no overlap row naming repo-kickoff")

    def session_start(self):
        return section(read(SKILL), "## Every session starts here")

    def test_session_start_runs_the_gate_as_a_numbered_step(self):
        self.assertTrue([line for line in self.session_start() if re.match(r"\d+\. .*check_gates\.py", line)])

    def test_companion_report_is_only_a_hint(self):
        line = next(line for line in self.session_start() if "check_companions.py" in line).lower()
        self.assertIn("hint", line)
        self.assertIn("session's own skill list", line)

    def test_new_project_runs_setup_before_stage_0(self):
        line = next(line for line in self.session_start() if "**Start:**" in line)
        self.assertLess(line.index("init_project.py"), line.index("Stage 0"))

    def test_router_companions_exist_in_mapping(self):
        unknown = named_companions(read(SKILL)) - all_names()
        self.assertEqual(unknown, set())


class StageFilesTest(unittest.TestCase):
    def test_same_names_as_principles(self):
        principles = sorted(p.name for p in (ROOT / "principles").glob("0*.md"))
        self.assertEqual(principles, list(STAGE_FILES))
        self.assertEqual(sorted(p.name for p in STAGES.glob("*.md")), list(STAGE_FILES))

    def test_five_headings_in_order(self):
        for name in STAGE_FILES:
            with self.subTest(name=name):
                lines = read(STAGES / name).splitlines()
                found = [line.strip() for line in lines if line.strip() in HEADINGS]
                self.assertEqual(found, list(HEADINGS))

    def test_named_companions_belong_to_the_stage(self):
        for n, name in enumerate(STAGE_FILES):
            with self.subTest(name=name):
                unknown = named_companions(read(STAGES / name)) - names_for_stage(n)
                self.assertEqual(unknown, set())

    def test_every_primary_of_the_stage_is_named(self):
        for n, name in enumerate(STAGE_FILES):
            text = read(STAGES / name)
            for row in companions():
                if n in row["stages"]:
                    with self.subTest(name=name, primary=row["primary"]):
                        self.assertIn(f"`{row['primary']}`", text)

    def test_design_questions_are_answered_in_the_owners_words(self):
        step = next(line for line in section(read(STAGES / "01-design.md"), "## Do") if line.startswith("1. "))
        self.assertIn("own words", step)

    def test_stage_specific_content(self):
        wanted = {
            "00-intake.md": ("separate session", "ATK-", "REQ-"),
            "04-verify.md": ("ladder", "rung 2", "by hand"),
            "05-ship.md": ("explain-back", "go-live", "re-confirm"),
            "06-own.md": ("closed-book", "separate session", "gap", "7 days"),
            "03-build.md": ("BUILD-LEDGER.md", "workspace"),
        }
        for name, needles in wanted.items():
            text = read(STAGES / name).lower()
            for needle in needles:
                with self.subTest(name=name, needle=needle):
                    self.assertIn(needle.lower(), text)


class LanguageTest(unittest.TestCase):
    def files(self):
        return [SKILL, *(STAGES / name for name in STAGE_FILES)]

    def test_no_gendered_pronouns(self):
        for path in self.files():
            with self.subTest(path=path.name):
                self.assertEqual(PRONOUNS.findall(read(path)), [])

    def test_pronoun_check_can_fire(self):
        self.assertTrue(PRONOUNS.findall("ask the owner what he wants"))


class ManifestTest(unittest.TestCase):
    def test_plugin_json(self):
        data = json.loads(read(PLUGIN))
        self.assertEqual(data["name"], "agentic-principles")
        self.assertEqual(data["version"], VERSION)
        self.assertEqual(data["skills"], ["./skills/agentic-principles"])
        for rel in data["skills"]:
            self.assertTrue((ROOT / rel).is_dir(), rel)
            self.assertTrue((ROOT / rel / "SKILL.md").is_file(), rel)

    def test_marketplace_json(self):
        data = json.loads(read(MARKETPLACE))
        self.assertEqual(data["metadata"]["version"], VERSION)
        plugins = data["plugins"]
        self.assertEqual([p["name"] for p in plugins], ["agentic-principles"])
        self.assertEqual(plugins[0]["version"], VERSION)
        self.assertTrue((ROOT / plugins[0]["source"]).is_dir())


if __name__ == "__main__":
    unittest.main()
