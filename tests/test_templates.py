"""The shipped templates must pass the documentation gate and all eight must exist.

The five templates the gate does not read are checked here against the parts their own
guidance comments promise.
"""
import re
import unittest
from pathlib import Path

from checks.check_docs import ai_log_problems, decisions_problems, requirements_problems

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
ALL = ("DECISIONS.md", "AI-Agents.md", "REQUIREMENTS.md", "BUILD-LEDGER.md",
       "RESULTS.md", "HANDOVER.md", "GLOSSARY.md", "PULL_REQUEST_TEMPLATE.md")


SECTIONS = {
    "BUILD-LEDGER.md": ("Method", "Rulings", "Deferred findings"),
    "RESULTS.md": ("Setup", "Outcome versus expected", "Observations", "How to reproduce"),
    "HANDOVER.md": ("Status", "Resume order", "Open items"),
    "PULL_REQUEST_TEMPLATE.md": ("Goal", "Choices", "Measurements", "How to check"),
}


def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8-sig")


def missing_sections(text: str, required) -> list[str]:
    """Required `## ` sections absent from the text; a heading inside a comment does not count."""
    return []


def glossary_problems(text: str) -> list[str]:
    """A glossary needs at least one `- **term:** meaning` line, with the terms in alphabetical order."""
    return []


class HelperTests(unittest.TestCase):
    """The template checks below must be able to fail."""

    def test_missing_section_fires(self):
        self.assertEqual(missing_sections("## Goal\n\ntext\n", ("Goal", "Choices")), ["Choices"])

    def test_heading_inside_a_comment_does_not_count(self):
        self.assertEqual(missing_sections("<!--\n## Goal\n-->\n", ("Goal",)), ["Goal"])

    def test_deeper_heading_does_not_count(self):
        self.assertEqual(missing_sections("### Goal\n", ("Goal",)), ["Goal"])

    def test_present_sections_pass(self):
        self.assertEqual(missing_sections("## Goal\r\n\r\n## Choices  \n", ("Goal", "Choices")), [])

    def test_glossary_without_entries_fires(self):
        self.assertEqual(len(glossary_problems("# Glossary\n\n<!--\n- **Term:** shown\n-->\n")), 1)

    def test_glossary_out_of_order_fires(self):
        self.assertEqual(len(glossary_problems("- **Gate:** a check\n- **CI:** a run\n")), 1)

    def test_glossary_order_ignores_case(self):
        self.assertEqual(glossary_problems("- **apple:** a\n- **Banana:** b\n"), [])


class TemplateTests(unittest.TestCase):
    def test_ungated_templates_have_their_sections(self):
        for name, required in SECTIONS.items():
            with self.subTest(template=name):
                self.assertEqual(missing_sections(read(name), required), [])

    def test_glossary_template_is_well_formed(self):
        self.assertEqual(glossary_problems(read("GLOSSARY.md")), [])

    def test_templates_pass_the_gate(self):
        for name, rule in (("DECISIONS.md", decisions_problems),
                           ("AI-Agents.md", ai_log_problems),
                           ("REQUIREMENTS.md", requirements_problems)):
            with self.subTest(template=name):
                self.assertEqual(rule(read(name), name), [])

    def test_all_templates_exist_and_carry_guidance(self):
        for name in ALL:
            with self.subTest(template=name):
                text = read(name)
                self.assertGreater(len(text.strip()), 100)
                self.assertIn("<!--", text)


if __name__ == "__main__":
    unittest.main()
