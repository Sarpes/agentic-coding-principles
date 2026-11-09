"""Tests for the engineering checklist (checklist/*.md) and its builder (build_checklist.py).

Each check in item_problems has a case that must fire and a look-alike that must not.
"""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "agentic-principles"
sys.path.insert(0, str(SKILL / "scripts"))

import build_checklist  # noqa: E402
from build_checklist import AREA_FILES, build, item_problems, main, parse_items  # noqa: E402

COMPANIONS = {"security-review", "property-based-testing:property-based-testing", "run"}


def item(ident="C-SEC-1", title="Keep secrets out of the code", **over):
    fields = {
        "Rule": "Keep every password and key outside the source code.",
        "Why it matters": "Code is copied and shared; a key inside it leaks with it.",
        "Applies when": "always",
        "How to validate": "Search the tracked files for key patterns; expect none.",
        "Companion": "security-review",
        "Source": "The Twelve-Factor App, III. Config, https://12factor.net/config",
    }
    fields.update(over)
    lines = [f"### {ident} {title}", ""]
    lines += [f"- **{label}:** {value}" for label, value in fields.items() if value is not None]
    return "\n".join(lines) + "\n"


def doc(*items):
    return "# Security\n\nIntro text.\n\n" + "\n".join(items)


class TestParseItems(unittest.TestCase):
    def test_parse_reads_id_title_line_and_fields(self):
        found = parse_items(doc(item()))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], "C-SEC-1")
        self.assertEqual(found[0]["title"], "Keep secrets out of the code")
        self.assertEqual(found[0]["line"], 5)
        self.assertEqual(found[0]["fields"]["Applies when"], "always")
        self.assertIn("https://12factor.net/config", found[0]["fields"]["Source"])

    def test_parse_reads_two_items_in_order(self):
        found = parse_items(doc(item(), item("C-SEC-2", "Second")))
        self.assertEqual([i["id"] for i in found], ["C-SEC-1", "C-SEC-2"])

    def test_parse_ignores_items_inside_a_code_fence(self):
        text = doc(item()) + "\n```\n" + item("C-SEC-2", "Example only") + "```\n"
        self.assertEqual([i["id"] for i in parse_items(text)], ["C-SEC-1"])

    def test_parse_ignores_items_inside_an_html_comment(self):
        text = doc(item()) + "\n<!--\n" + item("C-SEC-2", "Hidden") + "-->\n"
        self.assertEqual([i["id"] for i in parse_items(text)], ["C-SEC-1"])

    def test_parse_fields_stop_at_the_next_heading(self):
        text = doc(item(), "## Next section\n\n- **Rule:** not part of the item\n")
        self.assertNotIn("not part", parse_items(text)[0]["fields"]["Rule"])


class TestItemProblems(unittest.TestCase):
    def fires(self, text, fragment):
        problems = item_problems(text, COMPANIONS)
        self.assertTrue(any(fragment in p for p in problems), problems)

    def quiet(self, text):
        self.assertEqual(item_problems(text, COMPANIONS), [])

    def test_good_item_has_no_problems(self):
        self.quiet(doc(item()))

    def test_blank_field_fires(self):
        self.fires(doc(item(**{"Why it matters": ""})), "'Why it matters' is blank")

    def test_placeholder_field_fires(self):
        self.fires(doc(item(**{"How to validate": "TBD"})), "'How to validate' is blank")

    def test_placeholder_look_alike_with_words_is_quiet(self):
        self.quiet(doc(item(**{"How to validate": "TBD markers are searched for; expect none."})))

    def test_missing_field_fires(self):
        self.fires(doc(item(Rule=None)), "missing '- **Rule:**'")

    def test_missing_source_fires(self):
        self.fires(doc(item(Source=None)), "missing '- **Source:**'")

    def test_source_without_https_fires(self):
        self.fires(doc(item(Source="The Twelve-Factor App, http://12factor.net/config")), "https://")

    def test_source_with_only_an_address_fires(self):
        self.fires(doc(item(Source="https://12factor.net/config")), "name the source")

    def test_unknown_trait_fires(self):
        self.fires(doc(item(**{"Applies when": "web+blockchain"})), "unknown trait 'blockchain'")

    def test_known_traits_joined_with_plus_are_quiet(self):
        self.quiet(doc(item(**{"Applies when": "web+personal-data+llm"})))

    def test_always_combined_with_a_trait_fires(self):
        self.fires(doc(item(**{"Applies when": "always+web"})), "'always' stands alone")

    def test_companion_not_in_mapping_fires(self):
        self.fires(doc(item(Companion="made-up:skill")), "companion 'made-up:skill' is not in companions.json")

    def test_companion_none_is_quiet(self):
        self.quiet(doc(item(Companion="none")))

    def test_numbering_gap_fires(self):
        self.fires(doc(item(), item("C-SEC-3", "Third")), "expected C-SEC-2")

    def test_gapless_numbering_is_quiet(self):
        self.quiet(doc(item(), item("C-SEC-2", "Second")))

    def test_two_areas_in_one_file_fires(self):
        self.fires(doc(item(), item("C-DEP-2", "Other area")), "expected C-SEC-2")

    def test_malformed_heading_fires(self):
        self.fires(doc(item("C-sec-1", "Lower case area")), "is not in the form")

    def test_heading_without_title_fires(self):
        text = doc(item()).replace("### C-SEC-1 Keep secrets out of the code", "### C-SEC-1")
        self.fires(text, "is not in the form")

    def test_ordinary_heading_is_quiet(self):
        self.quiet(doc(item()) + "\n### Notes on checking\n\nSome text.\n")

    def test_file_with_no_items_fires(self):
        self.fires("# Security\n\nNothing here yet.\n", "no items")


class TestRealChecklist(unittest.TestCase):
    def setUp(self):
        rows = json.loads((SKILL / "companions.json").read_text(encoding="utf-8"))
        self.companions = {r["primary"] for r in rows} | {a for r in rows for a in r["also"]}

    def test_every_checklist_file_exists(self):
        for name in ["README.md", *AREA_FILES]:
            self.assertTrue((ROOT / "checklist" / name).is_file(), name)

    def test_each_area_file_has_no_problems(self):
        for name in AREA_FILES:
            text = (ROOT / "checklist" / name).read_text(encoding="utf-8")
            self.assertEqual(item_problems(text, self.companions), [], name)

    def test_ids_are_gapless_per_file_and_carry_the_file_area(self):
        for name, area in AREA_FILES.items():
            ids = [i["id"] for i in parse_items((ROOT / "checklist" / name).read_text(encoding="utf-8"))]
            self.assertEqual(ids, [f"C-{area}-{n}" for n in range(1, len(ids) + 1)], name)
            self.assertGreater(len(ids), 0, name)

    def test_total_item_count_is_sensible(self):
        self.assertTrue(25 <= len(build(ROOT)) <= 40, len(build(ROOT)))

    def test_each_area_of_design_section_8_has_an_item(self):
        titles = [i["title"].lower() for name in AREA_FILES
                  for i in parse_items((ROOT / "checklist" / name).read_text(encoding="utf-8"))]
        areas = {
            "integration testing": r"integration",
            "fuzz testing": r"fuzz",
            "load testing": r"load",
            "failure injection": r"failure",
            "clean-clone start": r"clean clone",
            "threat modelling": r"threat model",
            "access control": r"access",
            "input handling": r"input",
            "secrets": r"secret",
            "dependencies": r"dependenc",
            "logging": r"\blog",
            "monitoring": r"monitor",
            "error handling": r"error",
            "safe retries": r"retr",
            "data migrations": r"migration",
            "rollback": r"roll back",
            "backups": r"backup|restore",
            "prompt injection": r"prompt injection",
            "cost limits": r"cost",
            "output evaluation": r"evaluat",
        }
        for area, pattern in areas.items():
            self.assertTrue(any(re.search(pattern, t) for t in titles), area)

    def test_readme_holds_no_items(self):
        self.assertEqual(parse_items((ROOT / "checklist" / "README.md").read_text(encoding="utf-8")), [])


class TestBuild(unittest.TestCase):
    def test_generated_file_equals_build(self):
        data = json.loads((ROOT / "checklist" / "checklist.json").read_text(encoding="utf-8"))
        self.assertEqual(data, build(ROOT))

    def test_build_rows_hold_only_id_and_a_list_of_traits(self):
        for row in build(ROOT):
            self.assertEqual(set(row), {"id", "applies_when"})
            self.assertIsInstance(row["applies_when"], list)

    def test_build_ids_are_unique(self):
        ids = [row["id"] for row in build(ROOT)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_build_splits_traits_on_plus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), security=doc(item(**{"Applies when": "web+personal-data"})))
            rows = build(root)
        self.assertIn({"id": "C-SEC-1", "applies_when": ["web", "personal-data"]}, rows)

    def test_build_refuses_a_file_with_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), security=doc(item(Source=None)))
            with self.assertRaises(ValueError) as caught:
                build(root)
        self.assertIn("security.md", str(caught.exception))

    def test_build_refuses_a_missing_area_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            (root / "checklist" / "data.md").unlink()
            with self.assertRaises(ValueError) as caught:
                build(root)
        self.assertIn("data.md", str(caught.exception))

    def test_traits_come_from_the_gate_script(self):
        import check_gates
        self.assertEqual(build_checklist.TRAITS, set(check_gates.TRAIT_RULES) | {"personal-data"})


class TestMain(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_main_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            code, _ = self.run_main([str(root)])
            data = json.loads((root / "checklist" / "checklist.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(data, build(root))

    def test_check_fails_on_a_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            (root / "checklist" / "checklist.json").write_text("[]\n", encoding="utf-8")
            code, output = self.run_main(["--check", str(root)])
        self.assertEqual(code, 1)
        self.assertIn("out of date", output)

    def test_check_passes_on_a_fresh_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            self.run_main([str(root)])
            code, _ = self.run_main(["--check", str(root)])
        self.assertEqual(code, 0)

    def test_main_reports_problems_with_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), security=doc(item(Companion="made-up:skill")))
            code, output = self.run_main([str(root)])
        self.assertEqual(code, 1)
        self.assertIn("made-up:skill", output)


def make_root(base: Path, security: str | None = None) -> Path:
    """A minimal repository: the companion mapping and one valid item per area file."""
    (base / "skills" / "agentic-principles").mkdir(parents=True)
    shutil.copy(SKILL / "companions.json", base / "skills" / "agentic-principles" / "companions.json")
    folder = base / "checklist"
    folder.mkdir()
    for name, area in AREA_FILES.items():
        text = doc(item(f"C-{area}-1", f"Item for {area}"))
        if name == "security.md" and security is not None:
            text = security
        (folder / name).write_text(text, encoding="utf-8")
    return base


if __name__ == "__main__":
    unittest.main()
