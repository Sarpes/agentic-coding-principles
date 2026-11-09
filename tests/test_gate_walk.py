"""End to end: a project set up by init_project.py and filled in the way an owner following the templates' own
comments would fill it passes every stage of check_gates.py, on Small and on Full.

Only the worked-example lines of the real templates are replaced (the lines outside comments that carry the
(EXAMPLE) marker); every guidance comment stays as it was copied. After each stage is marked passed and
committed, check_project must report 0 problems. A template whose own comment trips its own gate, or a stage
that judges a section belonging to a later stage, fails this walk.
"""
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "agentic-principles" / "scripts"))

import check_gates  # noqa: E402
import init_project  # noqa: E402
from tests.test_check_gates import commit, git, ls  # noqa: E402

MARKER = check_gates.EXAMPLE_MARKER
TODAY = date(2026, 11, 10)
ALL_RUNGS = "tests/test_tool.py | tests/test_tool.py | tests/test_tool.py | tests/test_tool.py | tests/test_tool.py"
ATTACKS = ["Pass two strings instead of numbers.", "Pass None.", "Pass numbers too large for a float.",
           "Pass a boolean.", "Call it with one argument."]


def replace_examples(text, by_section, keep=()):
    """Replace the worked-example lines, section by section, with the owner's lines.

    An example line is a line outside an HTML comment that holds the marker. Its section is the `## ` heading
    above it ("" before the first one). Every example line of a section is removed and the section's new lines go
    where the first one was. A section in `keep` is left as it is. A section with example lines but no
    replacement, or a replacement with no example lines to replace, is an error: the template changed."""
    out, section, in_comment, found = [], "", False, set()
    for line in text.split("\n"):
        if not in_comment and line.startswith("## "):
            section = line[3:].strip()
        example = not in_comment and "<!--" not in line and MARKER in line and section not in keep
        if in_comment:
            in_comment = "-->" not in line
        elif "<!--" in line:
            in_comment = "-->" not in line.split("<!--", 1)[1]
        if not example:
            out.append(line)
            continue
        if section not in by_section:
            raise AssertionError(f"example line in section {section!r} has no replacement: {line}")
        if section not in found:
            out.extend(by_section[section])
            found.add(section)
    if set(by_section) - found:
        raise AssertionError(f"no example lines to replace in: {sorted(set(by_section) - found)}")
    return "\n".join(out)


def read(root, name):
    return (Path(root) / name).read_text(encoding="utf-8")


def pass_row(root, n, evidence):
    """STAGES.md text with stage n marked passed with this evidence."""
    name = check_gates.STAGE_NAMES[n]
    text, count = re.subn(rf"^\| {re.escape(name)} \| open \| - \| - \|$", f"| {name} | passed | {evidence} | - |",
                          read(root, "STAGES.md"), flags=re.M)
    if count != 1:
        raise AssertionError(f"no open row for {name} in STAGES.md")
    return text


def fill_lines(text, values):
    for label, value in values.items():
        text, count = re.subn(rf"^{re.escape(label)}:$", f"{label}: {value}", text, flags=re.M)
        if count != 1:
            raise AssertionError(f"no empty line '{label}:'")
    return text


class Walk:
    """One project walked from init to Stage 7, as an owner would walk it."""

    def __init__(self, case, size):
        self.case, self.size, self.full = case, size, size == "full"
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "proj"
        self.root.mkdir()
        git(self.root, "init", "-q")
        commit(self.root, {"tool.py": "def add(a, b):\n    return a + b\n",
                           "tests/test_tool.py": "import unittest\n"}, "first code")
        init_project.init(self.root, size, "normal")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "set up the process")
        self.template_architecture = read(self.root, "ARCHITECTURE.md")

    def assert_clean(self, label):
        problems, _ = check_gates.check_project(self.root, TODAY)
        self.case.assertEqual(problems, [], f"{self.size}: {label}")

    def stage(self, n, evidence, files, label):
        files = dict(files)
        files["STAGES.md"] = pass_row(self.root, n, evidence)
        commit(self.root, files, f"stage {n}")
        self.assert_clean(label)

    def intake(self):
        requirements = replace_examples(read(self.root, "REQUIREMENTS.md"), {"": [
            "| REQ-1 | add returns the sum of two numbers. | - | - | - | open |"]})
        count = 5 if self.full else 3
        attacks = replace_examples(read(self.root, "ATTACKS.md"), {"": [
            f"| ATK-{i} | {ATTACKS[i - 1]} | 3 | fresh session |" for i in range(1, count + 1)]})
        self.stage(0, "file:REQUIREMENTS.md, file:ATTACKS.md",
                   {"REQUIREMENTS.md": requirements, "ATTACKS.md": attacks}, "stage 0 Intake")

    def design(self):
        files = {"DECISIONS.md": replace_examples(read(self.root, "DECISIONS.md"), {"": [
            "### D1. Standard library only"]})}
        evidence = "file:DECISIONS.md"
        if self.full:
            files["docs/design.md"] = "# Design\n\nOne function, add(a, b), used by a script.\n"
            evidence += ", file:docs/design.md"
        self.stage(1, evidence, files, "stage 1 Design")

    def plan(self):
        name = "docs/plans/plan.md" if self.full else "PLAN.md"
        self.stage(2, f"file:{name}", {name: "# Plan\n\n1. Write add(). Done when its test passes.\n"},
                   "stage 2 Plan")

    def build(self):
        work = commit(self.root, {"tool.py": "def add(a, b):\n    \"\"\"The sum.\"\"\"\n    return a + b\n"}, "work")
        ledger = replace_examples(read(self.root, "BUILD-LEDGER.md"), {
            "Reviews": ["| 1. add() | A fresh session that did not write the code | Approved |"],
            "Rulings": ["### R1. One file for the tests"],
            "Deferred findings": ["| F1 | add accepts strings. | LEAVE | The callers pass numbers only. |"]})
        self.stage(3, f"commit:{work}, file:BUILD-LEDGER.md", {"BUILD-LEDGER.md": ledger}, "stage 3 Build")

    def architecture(self):
        parts = ["Adder", "REQ-1"] + [f"ATK-{i}" for i in range(1, (6 if self.full else 4))]
        return replace_examples(self.template_architecture, {
            "Diagram": ["numbers --> add() --> sum"],
            "Components": ["| Adder | Adds two numbers and returns the sum. |"],
            "File map": [f"| {path} | Part of the project. |" for path in ls(self.root)],
            "Tech stack": ["- Python 3.11, standard library only."],
            "Tests": [f"| {part} | {ALL_RUNGS} |" for part in parts],
            "Complex problems": ["- None so far."],
            "Dependencies": []})

    def verify(self):
        evidence = "file:ARCHITECTURE.md"
        if self.full:
            commit(self.root, {"RESULTS.md": "# Results\n\n## Setup\n\nRan the tests: 1 of 1 passed.\n"}, "results")
            evidence += ", file:RESULTS.md"
        self.stage(4, evidence, {"ARCHITECTURE.md": self.architecture()}, "stage 4 Verify")

    def ship(self):
        ownership = replace_examples(read(self.root, "OWNERSHIP.md"), {"Explain-back": [
            "| what-it-does | What does it do? | It adds two numbers for a script. | - | closed |",
            "| how-it-breaks | How does it break? | Strings are joined instead of added. | - | closed |",
            "| how-to-recover | What do you do first? | Revert the last commit and run the tests. | - | closed |"]},
            keep=("Full round",))
        files, evidence = {"OWNERSHIP.md": ownership}, "file:OWNERSHIP.md"
        if self.full:
            out, _ = check_gates.go_live_report(self.root)
            ids = [line.strip() for line in out if line.startswith("  ")]
            self.case.assertTrue(ids, out)
            files["GO-LIVE.md"] = replace_examples(read(self.root, "GO-LIVE.md"), {"": [
                f"| Risk named by {ident}. | Read the code. | {ident} | not applicable | one pure function with no "
                "outside input |" for ident in ids]})
            evidence += ", file:GO-LIVE.md"
        self.stage(5, evidence, files, "stage 5 Ship, Full round rows still the template's")

    def own(self):
        hand = commit(self.root, {"tool.py": "def add(a, b):\n    \"\"\"Return the sum.\"\"\"\n    return a + b\n"},
                      "the owner's own change")
        ownership = replace_examples(read(self.root, "OWNERSHIP.md"), {"Full round": [
            "| What does Adder do? | It returns a plus b. | - | closed |",
            "| Which file holds it? | tool.py. | - | closed |",
            "| Which package could you remove? | None; there are none. | - | closed |"]})
        ownership = fill_lines(ownership, {"Hand-changed commit": hand, "Closed": "2026-11-09",
                                           "Re-check due": "2026-11-16", "Re-check done": "-",
                                           "Graded by": "a fresh session that compared the answers with the code"})
        self.stage(6, "file:OWNERSHIP.md", {"OWNERSHIP.md": ownership}, "stage 6 Own")

    def retro(self):
        log = replace_examples(read(self.root, "AI-Agents.md"), {"": ["### 1. Writing add (2026-11-09)"]})
        log = log.rstrip("\n") + "\n\nThe one mistake became a rule: check install claims in a clean environment.\n"
        self.stage(7, "file:AI-Agents.md", {"AI-Agents.md": log}, "stage 7 Retro")

    def run(self, steps=None):
        self.assert_clean("right after init")
        for step in (steps or (self.intake, self.design, self.plan, self.build, self.verify, self.ship, self.own,
                               self.retro)):
            step()


class GateWalk(unittest.TestCase):
    def test_a_small_project_filled_in_from_the_templates_passes_every_stage(self):
        Walk(self, "small").run()

    def test_a_full_project_filled_in_from_the_templates_passes_every_stage(self):
        Walk(self, "full").run()

    def test_a_walked_project_whose_components_rows_are_deleted_is_refused(self):
        """Deleting the Components rows used to drop every component from the ladder and the full round silently."""
        walk = Walk(self, "full")
        walk.run((walk.intake, walk.design, walk.plan, walk.build, walk.verify))
        text = read(walk.root, "ARCHITECTURE.md")
        stripped = "\n".join(line for line in text.split("\n") if not line.startswith("| Adder |"))
        commit(walk.root, {"ARCHITECTURE.md": stripped}, "components deleted")
        problems, _ = check_gates.check_project(walk.root, TODAY)
        self.assertTrue(any("Components" in p.message for p in problems), problems)


class ReplaceExamplesHelper(unittest.TestCase):
    """The walk's helper must refuse a template it does not understand, or the walk could pass by accident."""

    def test_an_example_line_with_no_replacement_is_an_error(self):
        with self.assertRaises(AssertionError):
            replace_examples(f"## A\n\n| x {MARKER} |\n", {})

    def test_a_replacement_with_nothing_to_replace_is_an_error(self):
        with self.assertRaises(AssertionError):
            replace_examples("## A\n\n| x |\n", {"A": ["| y |"]})

    def test_marker_lines_inside_comments_are_kept(self):
        text = f"<!--\nrows marked {MARKER}\n-->\n## A\n\n| x {MARKER} |\n| z {MARKER} |\n"
        self.assertEqual(replace_examples(text, {"A": ["| y |"]}), f"<!--\nrows marked {MARKER}\n-->\n## A\n\n| y |\n")


if __name__ == "__main__":
    unittest.main()
