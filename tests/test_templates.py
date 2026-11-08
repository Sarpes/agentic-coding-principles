"""The shipped templates must pass the documentation gate and all eight must exist.

The five templates the gate does not read are checked here against the parts their own
guidance comments promise.
"""
import re
import sys
import unittest
from pathlib import Path

from checks.check_docs import ai_log_problems, decisions_problems, requirements_problems

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
sys.path.insert(0, str(TEMPLATES.parent / "skills" / "agentic-principles" / "scripts"))
from check_gates import (  # noqa: E402
    EXAMPLE_MARKER,
    attack_problems,
    attack_rungs,
    components,
    dependency_problems,
    file_map_problems,
)
from check_gates import test_table_problems as tt_problems  # noqa: E402  (not a test: a check function)

ALL = ("DECISIONS.md", "AI-Agents.md", "REQUIREMENTS.md", "BUILD-LEDGER.md",
       "RESULTS.md", "HANDOVER.md", "GLOSSARY.md", "PULL_REQUEST_TEMPLATE.md",
       "STAGES.md", "OVERRIDES.md", "ARCHITECTURE.md", "ATTACKS.md")


SECTIONS = {
    "ARCHITECTURE.md": ("Diagram", "Components", "File map", "Tech stack", "Tests", "Complex problems",
                        "Dependencies"),
    "BUILD-LEDGER.md": ("Method", "Rulings", "Deferred findings", "Reviews"),
    "RESULTS.md": ("Setup", "Outcome versus expected", "Observations", "How to reproduce"),
    "HANDOVER.md": ("Status", "Resume order", "Open items"),
    "PULL_REQUEST_TEMPLATE.md": ("Goal", "Choices", "Measurements", "How to check"),
}


def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8-sig")


def visible(text: str) -> str:
    """The text without its HTML comments, which hold guidance and not content."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def missing_sections(text: str, required) -> list[str]:
    """Required `## ` sections absent from the text; a heading inside a comment does not count."""
    found = {heading for heading in re.findall(r"^## (.+?)\s*$", visible(text), re.M)}
    return [section for section in required if section not in found]


def glossary_problems(text: str) -> list[str]:
    """A glossary needs at least one `- **term:** meaning` line, with the terms in alphabetical order."""
    terms = [term.casefold() for term in re.findall(r"^- \*\*(.+?):\*\*[ \t]*\S", visible(text), re.M)]
    if not terms:
        return ["no `- **term:** meaning` entry"]
    return [] if terms == sorted(terms) else ["terms are not in alphabetical order"]


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

    def test_attacks_template_parses_and_only_the_example_marker_fails_it(self):
        text = read("ATTACKS.md")
        problems = attack_problems(text, "full")
        self.assertGreaterEqual(len(problems), 1)
        self.assertTrue(all(EXAMPLE_MARKER in p.message for p in problems), problems)
        self.assertEqual(attack_problems(text.replace(EXAMPLE_MARKER, ""), "full"), [])
        self.assertTrue(set(attack_rungs(text.replace(EXAMPLE_MARKER, ""))) <= {"ATK-1", "ATK-2", "ATK-3", "ATK-4", "ATK-5"})

    def test_architecture_template_tables_have_the_columns_the_gate_reads(self):
        text = read("ARCHITECTURE.md")
        for header in ("| Component | What it does |", "| Path | What it does |",
                       "| Part | 1 Written first | 2 Catches breakage | 3 Input range | 4 Real integration "
                       "| 5 Deliberate failure |",
                       "| Name | Version | Why it is here | What breaks without it |"):
            with self.subTest(header=header):
                self.assertIn(header, visible(text))

    def test_architecture_template_examples_are_marked_and_fail_every_check(self):
        text = read("ARCHITECTURE.md")
        self.assertIn(EXAMPLE_MARKER, visible(text))
        parts = components(text) | {"REQ-1", "ATK-1"}
        self.assertTrue(components(text))
        self.assertTrue(file_map_problems(text, ["not-in-the-map.txt"], {}))
        self.assertTrue(dependency_problems(text, {"not-in-the-table": None}, [], {}))
        self.assertTrue(tt_problems(text, "small", parts, {}, [], TEMPLATES, {}))

    def test_all_templates_exist_and_carry_guidance(self):
        for name in ALL:
            with self.subTest(template=name):
                text = read(name)
                self.assertGreater(len(text.strip()), 100)
                self.assertIn("<!--", text)


if __name__ == "__main__":
    unittest.main()
