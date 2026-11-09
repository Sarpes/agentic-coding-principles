"""The README must name every plugin the skill maps, and only those, in one section.

`skills/agentic-principles/companions.json` is the single mapping of capabilities to installed
skills (design-skill section 5). The README section `## Works with these skills` tells a reader
which plugins to install; if the two drift apart, a reader is sent to a plugin the skill never
calls, or never told about one it does. The helper `readme_plugin_problems` is the gate, and
the look-alike tests below prove it can fail.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
COMPANIONS = ROOT / "skills" / "agentic-principles" / "companions.json"
SECTION = "## Works with these skills"
PLUGIN_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")
REQUIRED_HEADINGS = (
    "## Quick start",
    "## The eight stages",
    "## Install and start a project",
    "## Using it day to day",
    "## What a run looks like",
    "## The test ladder",
    "## Limits, stated openly",
    SECTION,
    "## How it is tested",
    "## Licence",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def mapping_plugins(rows: list[dict]) -> set[str]:
    """Plugin names the mapping calls: the part before ':' of a full name, and local skills.

    Built-ins (`run`, `security-review`) and file paths are not plugins and are not listed.
    """
    names = set()
    for row in rows:
        for name in [row["primary"], *row["also"]]:
            bare = name.lstrip("/")
            if ":" in bare:
                names.add(bare.split(":", 1)[0])
            elif row["kind"] == "local" and "/" not in bare:
                names.add(bare)
    return names


def section_text(readme: str, heading: str = SECTION) -> str | None:
    """Text of one '## ' section, or None when the heading is absent."""
    lines = readme.split("\n")
    if heading not in lines:
        return None
    body = []
    for line in lines[lines.index(heading) + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def section_names(section: str) -> set[str]:
    """Backticked plugin-like names inside the section."""
    return {t for t in re.findall(r"`([^`\n]+)`", section) if PLUGIN_TOKEN.match(t)}


def readme_plugin_problems(readme: str, rows: list[dict]) -> list[str]:
    section = section_text(readme)
    if section is None:
        return [f"README has no section '{SECTION}'"]
    wanted = mapping_plugins(rows)
    named = section_names(section)
    problems = [f"plugin in companions.json but not in the README section: {n}"
                for n in sorted(wanted - named)]
    problems += [f"plugin in the README section but not in companions.json: {n}"
                 for n in sorted(named - wanted)]
    return problems


ROWS = [
    {"primary": "alpha:one", "also": ["beta:two"], "kind": "skill"},
    {"primary": "/gamma:audit", "also": [], "kind": "command"},
    {"primary": "run", "also": [], "kind": "builtin"},
    {"primary": "repo-kickoff", "also": [], "kind": "local"},
    {"primary": "templates/PULL_REQUEST_TEMPLATE.md", "also": [], "kind": "local"},
]
GOOD = f"# T\n\n{SECTION}\n\n`alpha`, `beta`, `gamma` and `repo-kickoff`.\n\n## Licence\n\nMIT.\n"


class HelperTests(unittest.TestCase):
    """The gate must be able to fail, and must not fire on look-alikes."""

    def test_mapping_plugins_reads_prefixes_commands_and_local_skills(self):
        self.assertEqual(mapping_plugins(ROWS), {"alpha", "beta", "gamma", "repo-kickoff"})

    def test_complete_section_passes(self):
        self.assertEqual(readme_plugin_problems(GOOD, ROWS), [])

    def test_missing_plugin_fires(self):
        text = GOOD.replace("`beta`, ", "")
        self.assertEqual(readme_plugin_problems(text, ROWS),
                         ["plugin in companions.json but not in the README section: beta"])

    def test_unknown_plugin_fires(self):
        text = GOOD.replace("`gamma`", "`gamma`, `delta`")
        self.assertEqual(readme_plugin_problems(text, ROWS),
                         ["plugin in the README section but not in companions.json: delta"])

    def test_missing_section_fires(self):
        self.assertEqual(readme_plugin_problems("# T\n\n## Licence\n\nMIT.\n", ROWS),
                         [f"README has no section '{SECTION}'"])

    def test_name_outside_the_section_does_not_count(self):
        """Look-alike: a plugin named in another section is still missing from this one."""
        text = GOOD.replace("`beta`, ", "").replace("MIT.", "Uses `beta` too.")
        self.assertEqual(readme_plugin_problems(text, ROWS),
                         ["plugin in companions.json but not in the README section: beta"])

    def test_prose_words_and_paths_are_not_plugin_names(self):
        """Look-alike: plain words, and backticked paths or commands with a slash or a dot."""
        text = GOOD.replace("MIT.", "x").replace("and `repo-kickoff`.",
                                                  "and `repo-kickoff`. See `checks/check_docs.py` and fallback.")
        self.assertEqual(readme_plugin_problems(text, ROWS), [])

    def test_builtin_name_in_the_section_fires(self):
        """A built-in is not a plugin; naming it as one would send a reader to install nothing."""
        text = GOOD.replace("`gamma`", "`gamma`, `run`")
        self.assertEqual(readme_plugin_problems(text, ROWS),
                         ["plugin in the README section but not in companions.json: run"])

    def test_section_ends_at_the_next_heading(self):
        self.assertNotIn("MIT", section_text(GOOD))
        self.assertIsNone(section_text("# T\n\n## Other\n\nx\n"))


def table_problems(text: str) -> list[str]:
    """Every Markdown table whose delimiter row has a different cell count than its header."""
    problems = []
    lines = text.split("\n")
    fence = False
    for i, line in enumerate(lines[:-1]):
        if line.startswith("```"):
            fence = not fence
        nxt = lines[i + 1]
        if fence or not line.startswith("|") or not re.fullmatch(r"\|[ :|-]*-[ :|-]*\|", nxt):
            continue
        head, delim = line.strip().strip("|").split("|"), nxt.strip().strip("|").split("|")
        if len(head) != len(delim):
            problems.append(f"line {i + 1}: header has {len(head)} cells, delimiter row {len(delim)}")
    return problems


class TableTests(unittest.TestCase):
    def test_mismatched_delimiter_fires(self):
        self.assertEqual(table_problems("| a | b | c |\n|---|---|---|---|\n| 1 | 2 | 3 |\n"),
                         ["line 1: header has 3 cells, delimiter row 4"])

    def test_matching_delimiter_passes(self):
        self.assertEqual(table_problems("| a | b |\n|---|---|\n| 1 | 2 |\n"), [])

    def test_pipe_lines_that_are_not_tables_pass(self):
        self.assertEqual(table_problems("| not a table |\nplain text\n"), [])

    def test_every_table_in_the_readme_is_well_formed(self):
        self.assertEqual(table_problems(read(README)), [])


class RealReadmeTests(unittest.TestCase):
    def setUp(self):
        self.readme = read(README)
        self.rows = json.loads(COMPANIONS.read_text(encoding="utf-8"))

    def test_plugins_in_readme_match_companions_json(self):
        self.assertEqual(readme_plugin_problems(self.readme, self.rows), [])

    def test_named_authors_are_present(self):
        named = section_names(section_text(self.readme))
        for name in ("andrej-karpathy-skills", "mattpocock-skills", "superpowers"):
            self.assertIn(name, named)

    def test_required_headings_are_present(self):
        lines = self.readme.split("\n")
        for heading in REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, lines)

    def test_limits_are_stated_openly(self):
        limits = section_text(self.readme, "## Limits, stated openly").lower()
        for phrase in ("one git identity", "trust", "hook", "failed before",
                       "prose", "hint", "mutation", "workflow", "installed"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, limits)

    def test_no_machine_paths_and_no_release_claim(self):
        self.assertIsNone(re.search(r"[A-Za-z]:\\|/Users/|/home/", self.readme))
        self.assertNotRegex(self.readme, r"(?i)v?0\.2\.0")

    def test_every_skill_file_the_readme_links_exists(self):
        for target in re.findall(r"\]\(([^)#\s]+)\)", self.readme):
            if "://" in target:
                continue
            with self.subTest(target=target):
                self.assertTrue((ROOT / target).exists(), f"README links a missing path: {target}")


class UsageTests(unittest.TestCase):
    """A newcomer must find how to start before the reference material, and what each session does."""

    def setUp(self):
        self.readme = read(README)
        self.lines = self.readme.split("\n")

    def test_quick_start_comes_before_the_stage_table(self):
        self.assertLess(self.lines.index("## Quick start"), self.lines.index("## The eight stages"))

    def test_quick_start_has_the_install_commands_and_a_first_sentence(self):
        quick = section_text(self.readme, "## Quick start") or ""
        self.assertIn("/plugin marketplace add Sarpes/agentic-engineering-principles", quick)
        self.assertIn("/plugin install agentic-engineering-principles@agentic-engineering-principles", quick)
        self.assertIn("agentic principles", quick.lower())

    def test_daily_use_names_what_a_session_runs_and_what_the_owner_says(self):
        daily = (section_text(self.readme, "## Using it day to day") or "").lower()
        for needle in ("check_gates.py", "check_companions.py", "stages.md", "overrides.md", "glossary.md",
                       "adopt", "skip", "new cycle", "re-check", "never"):
            with self.subTest(needle=needle):
                self.assertIn(needle, daily)

    def test_daily_use_lists_the_owner_files(self):
        daily = section_text(self.readme, "## Using it day to day") or ""
        for name in ("STAGES.md", "REQUIREMENTS.md", "ATTACKS.md", "ARCHITECTURE.md", "DECISIONS.md",
                     "OVERRIDES.md", "GO-LIVE.md", "OWNERSHIP.md", "GLOSSARY.md", "BUILD-LEDGER.md"):
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", daily)

    def test_install_note_is_current(self):
        self.assertNotIn("has not yet been installed from the marketplace", self.readme)


class ChangelogTests(unittest.TestCase):
    def test_release_0_2_0_lists_the_skill_and_unreleased_is_empty(self):
        text = read(ROOT / "CHANGELOG.md")
        match = re.search(r"^## \[0\.2\.0\] - \d{4}-\d{2}-\d{2}$", text, re.M)
        if match is None:
            self.fail("no dated 0.2.0 section")
        released = text[match.end():].split("\n## ", 1)[0]
        self.assertIn("skills/agentic-principles", released)
        unreleased = text.split("## Unreleased", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(unreleased.strip(), "")
        self.assertLess(text.index("## Unreleased"), match.start())


if __name__ == "__main__":
    unittest.main()
