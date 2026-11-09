"""CREDITS.md must credit every outside project the skill names, and the formats this repository follows.

The owner's rule (2026-11-10): cite every source, give credit where it is due, never take anyone's work. A credit list
kept by hand drifts, so this test derives the names from companions.json and fails when one has no row.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREDITS = ROOT / "CREDITS.md"
COMPANIONS = ROOT / "skills" / "agentic-principles" / "companions.json"
COLUMNS = ["Plugin", "Author", "Source", "Licence", "Used here"]


def companion_plugins() -> set[str]:
    """The plugin (or built-in command) behind every companion name: the part before ':', without a leading '/'.
    A path into this repository (templates/...) is this repository's own file and needs no credit."""
    names = set()
    for row in json.loads(COMPANIONS.read_text(encoding="utf-8")):
        for name in [row["primary"], *row.get("also", [])]:
            if "/" in name.lstrip("/"):
                continue
            names.add(name.lstrip("/").split(":")[0])
    return names


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(body: str) -> list[list[str]]:
    lines = [line for line in body.splitlines() if line.startswith("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    return [r for r in rows[2:]] if len(rows) >= 2 else []


class CreditsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(CREDITS.is_file(), "CREDITS.md is missing")
        self.text = CREDITS.read_text(encoding="utf-8")

    def test_companion_table_has_the_columns(self):
        lines = [l for l in section(self.text, "Companion skills").splitlines() if l.startswith("|")]
        self.assertTrue(lines, "no table under '## Companion skills'")
        self.assertEqual([c.strip() for c in lines[0].strip("|").split("|")], COLUMNS)

    def test_every_companion_plugin_is_credited_with_a_source_and_a_licence(self):
        rows = {r[0].strip("` "): r for r in table_rows(section(self.text, "Companion skills"))}
        missing = sorted(companion_plugins() - set(rows))
        self.assertEqual(missing, [], "companions with no row in CREDITS.md")
        for name, cells in rows.items():
            with self.subTest(plugin=name):
                self.assertEqual(len(cells), len(COLUMNS))
                self.assertTrue(cells[1], "Author is blank")
                self.assertIn("https://", cells[2], "Source needs an https address")
                self.assertTrue(cells[3], "Licence is blank; write what the source states, or that it states none")

    def test_formats_this_repository_follows_are_credited(self):
        body = section(self.text, "Formats and ideas")
        for needle in ("Keep a Changelog", "Olivier Lacan", "https://keepachangelog.com",
                       "Documenting Architecture Decisions", "Michael Nygard"):
            self.assertIn(needle, body)

    def test_the_checklist_sources_are_pointed_to(self):
        self.assertIn("checklist/README.md", section(self.text, "Checklist sources"))

    def test_nothing_is_claimed_as_copied_without_saying_so(self):
        self.assertIn("No text or code from these projects is copied", self.text)

    def test_readme_links_the_credits(self):
        self.assertIn("(CREDITS.md)", (ROOT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
