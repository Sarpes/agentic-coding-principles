"""The shipped templates must pass the documentation gate and all eight must exist."""
import unittest
from pathlib import Path

from checks.check_docs import ai_log_problems, decisions_problems, requirements_problems

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
ALL = ("DECISIONS.md", "AI-Agents.md", "REQUIREMENTS.md", "BUILD-LEDGER.md",
       "RESULTS.md", "HANDOVER.md", "GLOSSARY.md", "PULL_REQUEST_TEMPLATE.md")


def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8-sig")


class TemplateTests(unittest.TestCase):
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
