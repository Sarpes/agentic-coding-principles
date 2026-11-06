"""Tests for the documentation gate. All inputs are built as strings here."""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from checks import check_docs
from checks.check_docs import (
    Problem,
    ai_log_problems,
    check_repo,
    decisions_problems,
    main,
    requirements_problems,
)

SCRIPT = Path(check_docs.__file__)
FENCE = "`" * 3

DECISION_LABELS = ("Context", "Options considered", "Chosen", "Why", "Rejected",
                   "Cost / trade-off", "What would make you change it")
LOG_LABELS = ("Prompt (or summary of it)", "What the AI produced", "What I kept",
              "What I changed or rejected, and why",
              "Where the AI was wrong, and how I noticed")
SECTIONS = "## Assumptions\n\n- one\n\n## Not done (and why)\n\n- two\n"


def fields(labels, skip=(), override=None):
    override = override or {}
    return [f"- **{label}:** {override.get(label, 'text')}" for label in labels if label not in skip]


def decision(n, skip=(), override=None, heading=None):
    head = heading or f"### D{n}. Title {n}"
    return "\n".join([head, ""] + fields(DECISION_LABELS, skip, override)) + "\n"


def log_entry(n, skip=(), override=None):
    return "\n".join([f"### {n}. Title {n} (2026-11-06)", ""] + fields(LOG_LABELS, skip, override)) + "\n"


def decisions_doc(*entries, sections=SECTIONS):
    return "# Decisions\n\n" + "\n".join(entries) + "\n" + sections


def log_doc(*entries):
    return "# Log\n\n" + "\n".join(entries)


def line_of(text, needle):
    for number, line in enumerate(text.split("\n"), start=1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} not in text")


REQ_HEAD = "| ID | Requirement | Decision | Test | Evidence | Status |\n|---|---|---|---|---|---|\n"


def req_table(*rows):
    return "# Requirements\n\n" + REQ_HEAD + "".join(rows)


class DecisionRules(unittest.TestCase):
    def test_valid_document_passes(self):
        self.assertEqual(decisions_problems(decisions_doc(decision(1), decision(2))), [])

    def test_problem_is_a_named_tuple(self):
        p = Problem("a", 3, "m")
        self.assertEqual((p.file, p.line, p.message), ("a", 3, "m"))

    def test_missing_field_reported_at_entry_heading(self):
        text = decisions_doc(decision(1), decision(2, skip=("Why",)))
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].file, "DECISIONS.md")
        self.assertEqual(probs[0].line, line_of(text, "### D2."))
        self.assertIn("D2", probs[0].message)
        self.assertIn("- **Why:**", probs[0].message)

    def test_file_name_is_passed_through(self):
        probs = decisions_problems("", file="X.md")
        self.assertTrue(probs)
        self.assertTrue(all(p.file == "X.md" for p in probs))

    def test_bare_placeholders_rejected(self):
        for bare in ("None", "none.", "N/A", "TBD", "TODO", "-", "..."):
            with self.subTest(bare=bare):
                text = decisions_doc(decision(1, override={"Cost / trade-off": bare}))
                probs = decisions_problems(text)
                self.assertEqual(len(probs), 1)
                self.assertEqual(probs[0].line, line_of(text, "### D1."))
                self.assertIn("Cost / trade-off", probs[0].message)

    def test_none_with_reason_accepted(self):
        text = decisions_doc(decision(1, override={"Cost / trade-off": "None: nothing is lost."}))
        self.assertEqual(decisions_problems(text), [])

    def test_empty_field_rejected(self):
        text = decisions_doc(decision(1, override={"Why": ""}))
        self.assertEqual(len(decisions_problems(text)), 1)

    def test_numbering_gap_reported_at_the_out_of_place_heading(self):
        text = decisions_doc(decision(1), decision(3))
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, line_of(text, "### D3."))
        self.assertIn("numbering", probs[0].message)

    def test_duplicate_number_reported_at_second_heading(self):
        first, second = decision(1), decision(1)
        text = decisions_doc(first, second)
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, text[:text.rindex("### D1.")].count("\n") + 1)
        self.assertIn("numbering", probs[0].message)

    def test_grouped_heading_is_one_problem(self):
        grouped = "### D2-D3. Two things at once\n\n" + "\n".join(fields(DECISION_LABELS)) + "\n"
        text = decisions_doc(decision(1), grouped)
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, line_of(text, "### D2-D3."))
        self.assertIn("one decision per entry", probs[0].message)

    def test_missing_sections_reported_individually(self):
        no_assumptions = decisions_doc(decision(1), sections="## Not done (and why)\n\n- x\n")
        no_not_done = decisions_doc(decision(1), sections="## Assumptions\n\n- x\n")
        neither = decisions_doc(decision(1), sections="")
        for text, expected in ((no_assumptions, ["## Assumptions"]),
                               (no_not_done, ["## Not done (and why)"]),
                               (neither, ["## Assumptions", "## Not done (and why)"])):
            with self.subTest(expected=expected):
                probs = decisions_problems(text)
                self.assertEqual(len(probs), len(expected))
                for p, name in zip(probs, expected):
                    self.assertEqual(p.line, 0)
                    self.assertIn(name, p.message)

    def test_section_with_trailing_spaces_is_found(self):
        text = decisions_doc(decision(1), sections="## Assumptions  \n\n## Not done (and why)\t\n")
        self.assertEqual(decisions_problems(text), [])

    def test_zero_entries_reported(self):
        probs = decisions_problems("# Decisions\n\n" + SECTIONS)
        self.assertEqual(len(probs), 1)
        self.assertIn("no decision", probs[0].message)

    def test_crlf_same_result(self):
        broken = decisions_doc(decision(1), decision(2, skip=("Why",)), decision(4))
        lf = decisions_problems(broken)
        crlf = decisions_problems(broken.replace("\n", "\r\n"))
        self.assertTrue(lf)
        self.assertEqual(lf, crlf)
        self.assertEqual(decisions_problems(decisions_doc(decision(1)).replace("\n", "\r\n")), [])

    def test_bom_and_non_ascii(self):
        turkish = decisions_doc(decision(1, override={"Why": "Çünkü şğıöü İ ışık."}),
                                decision(2, skip=("Chosen",)))
        plain = decisions_problems(turkish)
        with_bom = decisions_problems("﻿" + turkish)
        self.assertEqual(len(plain), 1)
        self.assertEqual(plain, with_bom)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DECISIONS.md").write_bytes(("﻿" + turkish).encode("utf-8"))
            (root / "AI-Agents.md").write_bytes(("﻿" + log_doc(log_entry(1))).encode("utf-8"))
            self.assertEqual(check_repo(root), plain)

    def test_fenced_examples_ignored(self):
        example = f"{FENCE}markdown\n### D9. Example only\n\n- **Why:** x\n{FENCE}\n"
        text = decisions_doc(decision(1), example + "\n" + decision(2, skip=("Why",)))
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, line_of(text, "### D2."))
        self.assertIn("D2", probs[0].message)

    def test_fenced_example_does_not_satisfy_a_field(self):
        shown = f"{FENCE}\n- **Why:** shown in an example\n{FENCE}\n"
        text = decisions_doc(decision(1, skip=("Why",)).rstrip("\n") + "\n" + shown)
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertIn("- **Why:**", probs[0].message)

    def test_near_miss_label_named(self):
        for bad in ("- **why:** text", "**Why**: text", "- **Why**: text", "- **WHY:** text"):
            with self.subTest(bad=bad):
                body = "\n".join(l if "**Why:**" not in l else bad for l in decision(1).split("\n"))
                text = decisions_doc(body)
                probs = decisions_problems(text)
                self.assertEqual(len(probs), 1)
                self.assertIn("- **Why:**", probs[0].message)
                self.assertIn("expected", probs[0].message)
                self.assertEqual(probs[0].line, line_of(text, bad))

    def test_unrelated_text_is_not_a_near_miss(self):
        text = decisions_doc(decision(1, skip=("Why",)))
        probs = decisions_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertNotIn("expected", probs[0].message)
        self.assertEqual(probs[0].line, line_of(text, "### D1."))


class AiLogRules(unittest.TestCase):
    def test_valid_log_passes(self):
        self.assertEqual(ai_log_problems(log_doc(log_entry(1), log_entry(2))), [])

    def test_missing_field(self):
        text = log_doc(log_entry(1), log_entry(2, skip=("What I kept",)))
        probs = ai_log_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].file, "AI-Agents.md")
        self.assertEqual(probs[0].line, line_of(text, "### 2."))
        self.assertIn("- **What I kept:**", probs[0].message)

    def test_empty_field(self):
        text = log_doc(log_entry(1, override={"What I kept": ""}))
        probs = ai_log_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertIn("empty", probs[0].message)

    def test_bare_none_allowed_in_log(self):
        text = log_doc(log_entry(1, override={"What I kept": "None"}))
        self.assertEqual(ai_log_problems(text), [])

    def test_numbering_gap(self):
        text = log_doc(log_entry(1), log_entry(3))
        probs = ai_log_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, line_of(text, "### 3."))

    def test_zero_entries(self):
        probs = ai_log_problems("# Log\n")
        self.assertEqual(len(probs), 1)
        self.assertIn("no entry", probs[0].message)

    def test_fenced_entry_ignored(self):
        example = f"{FENCE}\n### 7. Example\n{FENCE}\n"
        text = log_doc(log_entry(1), example)
        self.assertEqual(ai_log_problems(text), [])

    def test_crlf_same_result(self):
        broken = log_doc(log_entry(1, skip=("What I kept",)), log_entry(3))
        self.assertEqual(ai_log_problems(broken), ai_log_problems(broken.replace("\n", "\r\n")))

    def test_near_miss_label_named(self):
        body = "\n".join(l if "**What I kept:**" not in l else "- **what i kept:** text"
                         for l in log_entry(1).split("\n"))
        text = log_doc(body)
        probs = ai_log_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertIn("- **What I kept:**", probs[0].message)
        self.assertEqual(probs[0].line, line_of(text, "- **what i kept:**"))


class RequirementsRules(unittest.TestCase):
    GOOD = "| R1 | It does a thing | D1 | test_thing | run 12 | met |\n"

    def test_valid_table(self):
        rows = self.GOOD + "| R2 | Later | D2 | - | - | open |\n| R3 | Skipped | D3 | - | - | not done |\n"
        self.assertEqual(requirements_problems(req_table(rows)), [])

    def test_empty_cell(self):
        text = req_table("| R1 | It does a thing |  | test | ev | met |\n")
        probs = requirements_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].file, "REQUIREMENTS.md")
        self.assertEqual(probs[0].line, line_of(text, "| R1 |"))
        self.assertIn("Decision", probs[0].message)

    def test_bad_status(self):
        text = req_table("| R1 | x | D1 | t | e | done |\n")
        probs = requirements_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, line_of(text, "| R1 |"))
        self.assertIn("Status", probs[0].message)

    def test_met_without_evidence(self):
        for row in ("| R1 | x | D1 | t | - | met |\n", "| R1 | x | D1 | - | e | met |\n"):
            with self.subTest(row=row):
                probs = requirements_problems(req_table(row))
                self.assertEqual(len(probs), 1)
                self.assertIn("met", probs[0].message)

    def test_open_with_dashes_is_fine(self):
        self.assertEqual(requirements_problems(req_table("| R1 | x | D1 | - | - | open |\n")), [])

    def test_wrong_cell_count(self):
        probs = requirements_problems(req_table("| R1 | x | D1 | t | met |\n"))
        self.assertEqual(len(probs), 1)
        self.assertIn("6", probs[0].message)

    def test_requirements_header_rows_skipped(self):
        for align in ("|---|---|---|---|---|---|", "| :--- | ---: | :---: | --- | --- | --- |"):
            with self.subTest(align=align):
                text = ("# R\n\n| ID | Requirement | Decision | Test | Evidence | Status |\n"
                        f"{align}\n" + self.GOOD)
                self.assertEqual(requirements_problems(text), [])

    def test_wrong_header(self):
        text = "| ID | Requirement | Status |\n|---|---|---|\n| R1 | x | open |\n"
        probs = requirements_problems(text)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, 1)
        self.assertIn("columns", probs[0].message)

    def test_no_table(self):
        probs = requirements_problems("# Requirements\n\nnothing yet\n")
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0].line, 0)

    def test_fenced_table_ignored(self):
        shown = f"{FENCE}\n| R1 | x | D1 | t | e | wrong |\n{FENCE}\n"
        text = req_table(self.GOOD) + shown
        self.assertEqual(requirements_problems(text), [])

    def test_crlf_same_result(self):
        text = req_table("| R1 | x | D1 | t | - | met |\n")
        self.assertEqual(requirements_problems(text), requirements_problems(text.replace("\n", "\r\n")))


class RepoCheck(unittest.TestCase):
    def write(self, root, name, text):
        (Path(root) / name).write_text(text, encoding="utf-8", newline="")

    def test_missing_files_reported_at_line_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            probs = check_repo(Path(tmp))
        self.assertEqual({p.file for p in probs}, {"DECISIONS.md", "AI-Agents.md"})
        self.assertTrue(all(p.line == 0 and "missing" in p.message for p in probs))

    def test_valid_repo_passes_without_requirements_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "DECISIONS.md", decisions_doc(decision(1)))
            self.write(tmp, "AI-Agents.md", log_doc(log_entry(1)))
            self.assertEqual(check_repo(Path(tmp)), [])

    def test_requirements_checked_only_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "DECISIONS.md", decisions_doc(decision(1)))
            self.write(tmp, "AI-Agents.md", log_doc(log_entry(1)))
            self.write(tmp, "REQUIREMENTS.md", req_table("| R1 | x | D1 | t | - | met |\n"))
            probs = check_repo(Path(tmp))
        self.assertEqual([p.file for p in probs], ["REQUIREMENTS.md"])

    def test_problems_from_each_file_are_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "DECISIONS.md", decisions_doc(decision(1, skip=("Why",))))
            self.write(tmp, "AI-Agents.md", log_doc(log_entry(1, skip=("What I kept",))))
            probs = check_repo(Path(tmp))
        self.assertEqual([p.file for p in probs], ["DECISIONS.md", "AI-Agents.md"])

    def test_this_repository_passes(self):
        self.assertEqual(check_repo(SCRIPT.parent.parent), [])


class MisformedHeadings(unittest.TestCase):
    def test_decision_misforms_fire(self):
        for bad in ("### D2 Title", "## D2.", "#### D2.", "### D2.Title", "###D2. Title"):
            with self.subTest(bad=bad):
                text = decisions_doc(decision(1), decision(2, heading=bad))
                probs = decisions_problems(text)
                hits = [p for p in probs if p.line == line_of(text, bad) and "### D<number>. " in p.message]
                self.assertEqual(len(hits), 1, probs)

    def test_ai_log_misforms_fire(self):
        for bad in ("### 2 Title", "## 2.", "### 2) Title", "#### 2. Title"):
            with self.subTest(bad=bad):
                text = log_doc(log_entry(1), bad + "\n\n" + "\n".join(fields(LOG_LABELS)) + "\n")
                probs = ai_log_problems(text)
                hits = [p for p in probs if p.line == line_of(text, bad) and "### <number>. " in p.message]
                self.assertEqual(len(hits), 1, probs)

    def test_unrelated_headings_do_not_fire(self):
        self.assertEqual(decisions_problems(decisions_doc(decision(1), "## Decision list\n\ntext\n")), [])
        self.assertEqual(ai_log_problems(log_doc(log_entry(1), "### 2026 plans\n\ntext\n")), [])

    def test_correct_headings_do_not_fire(self):
        self.assertEqual(decisions_problems(decisions_doc(decision(1), decision(2))), [])
        self.assertEqual(ai_log_problems(log_doc(log_entry(1), log_entry(2))), [])


class CommandLine(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_exit_0_on_good_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "DECISIONS.md").write_text(decisions_doc(decision(1)), encoding="utf-8")
            (Path(tmp) / "AI-Agents.md").write_text(log_doc(log_entry(1)), encoding="utf-8")
            code, out, _ = self.run_main([tmp])
        self.assertEqual((code, out), (0, ""))

    def test_exit_1_prints_file_line_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = decisions_doc(decision(1, skip=("Why",)))
            (Path(tmp) / "DECISIONS.md").write_text(text, encoding="utf-8")
            (Path(tmp) / "AI-Agents.md").write_text(log_doc(log_entry(1)), encoding="utf-8")
            code, out, _ = self.run_main([tmp])
        self.assertEqual(code, 1)
        first = out.splitlines()[0]
        self.assertTrue(first.startswith(f"DECISIONS.md:{line_of(text, '### D1.')}: "), first)

    def test_exit_2_when_not_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.run_main([str(Path(tmp) / "nope")])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err)

    def test_exit_2_without_arguments(self):
        self.assertEqual(self.run_main([])[0], 2)

    def test_cli_exit_1_on_broken_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "DECISIONS.md").write_text(decisions_doc(decision(1, skip=("Why",))), encoding="utf-8")
            (Path(tmp) / "AI-Agents.md").write_text(log_doc(log_entry(1)), encoding="utf-8")
            done = subprocess.run([sys.executable, str(SCRIPT), tmp], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("DECISIONS.md:", done.stdout)

    def test_cli_exit_0_on_this_repository(self):
        done = subprocess.run([sys.executable, str(SCRIPT), str(SCRIPT.parent.parent)],
                              capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
