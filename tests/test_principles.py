"""The principles must follow the format of design section 6 and publish no private names.

Format per principle: a heading `### P<stage>.<n> <title>` followed by four bullets
(Rule, Why (incident), How to check, Enforced by). Ids run 1, 2, 3 ... in each stage file,
and every id appears in the index `principles/README.md`, which links every stage file.

The forbidden-names check reads the names from the environment variable
ACP_FORBIDDEN_NAMES (comma-separated). The list is never written into this repository,
because a list in a public file would itself publish the names; without the variable the
check is skipped with a visible reason.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRINCIPLES = ROOT / "principles"
STAGE_FILES = ("00-intake.md", "01-design.md", "02-plan.md", "03-build.md",
               "04-verify.md", "05-ship.md", "06-own.md", "07-retro.md")
FIELDS = ("Rule", "Why (incident)", "How to check", "Enforced by")
ENFORCERS = ("template", "check_docs", "CI", "human gate", "pre-commit hook", "contract hook (planned, v0.2)")
# Files that state the current total; the changelog and the logs record what was true at the time.
COUNT_FILES = ("README.md", "principles/README.md")
EMPTY_STAGE = "awaiting a real incident"
NO_INCIDENT = "no single measured incident"

HEADING = re.compile(r"^### (P(\d+)\.(\d+)) (\S.*)$")
FIELD = re.compile(r"^- \*\*(.+?):\*\*[ \t]*(.*)$")
INTERNAL_CODE = re.compile(r"\b[A-E]\d{1,2}\b")
ID_IN_INDEX = re.compile(r"\bP\d+\.\d+\b")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def principles(text: str) -> list[dict]:
    """Each principle as {id, stage, n, title, line, fields: [(name, value), ...]}."""
    out = []
    current = None
    for number, line in enumerate(text.split("\n"), start=1):
        m = HEADING.match(line)
        if m:
            current = {"id": m.group(1), "stage": int(m.group(2)), "n": int(m.group(3)),
                       "title": m.group(4), "line": number, "fields": []}
            out.append(current)
        elif line.startswith("#"):
            current = None
        elif current is not None:
            f = FIELD.match(line)
            if f:
                current["fields"].append((f.group(1), f.group(2).strip()))
    return out


def enforcer_problems(value: str) -> list[str]:
    """Kinds in an 'Enforced by' value that are not one of the five allowed kinds."""
    parts = [p.strip() for p in value.rstrip(".").split("+")]
    return [p for p in parts if p not in ENFORCERS]


def defined_kinds(index: str) -> list[str]:
    """First column of the table under '## Enforcement kinds' in the index."""
    section = index.split("## Enforcement kinds", 1)[1].split("\n## ", 1)[0]
    cells = re.findall(r"^\| *([^|]+?) *\|", section, re.M)
    return [c for c in cells if c != "Kind" and not set(c) <= {"-", ":"}]


def wrong_counts(text: str, actual: int) -> list[str]:
    """Every 'N principles' in the text whose N is not the actual total."""
    return [f"{n} principles" for n in re.findall(r"\b(\d+) principles\b", text) if int(n) != actual]


def forbidden_hits(text: str, names: list[str]) -> list[str]:
    """Names (case-insensitive) that occur anywhere in the text."""
    low = text.lower()
    return [n for n in names if n and n.lower() in low]


def forbidden_in_tracked_files(root: Path, names: list[str]) -> list[str]:
    """'file: name' for every name found in a file that git tracks under root."""
    files = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True,
                           check=True).stdout.decode("utf-8").split("\0")
    hits = []
    for rel in filter(None, files):
        path = root / rel
        if path.is_file():
            text = path.read_bytes().decode("utf-8", errors="replace")
            hits += [f"{rel}: {n}" for n in forbidden_hits(text, names)]
    return hits


class PrincipleFormatTests(unittest.TestCase):
    def test_stage_files_and_index_exist(self):
        for name in ("README.md",) + STAGE_FILES:
            with self.subTest(file=name):
                self.assertTrue((PRINCIPLES / name).is_file(), f"missing principles/{name}")

    def test_principles_format(self):
        for name in STAGE_FILES:
            stage = int(name[:2])
            text = read(PRINCIPLES / name)
            items = principles(text)
            with self.subTest(file=name):
                if not items:
                    self.assertIn(EMPTY_STAGE, text,
                                  f"{name}: a stage without principles must say it is {EMPTY_STAGE}")
                self.assertEqual([p["n"] for p in items], list(range(1, len(items) + 1)),
                                 f"{name}: ids not contiguous from 1")
            for p in items:
                with self.subTest(file=name, id=p["id"]):
                    self.assertEqual(p["stage"], stage, f"{name}:{p['line']}: wrong stage")
                    self.assertEqual(tuple(f for f, _ in p["fields"]), FIELDS,
                                     f"{name}:{p['line']}: fields must be {FIELDS}")
                    for field, value in p["fields"]:
                        self.assertTrue(value, f"{name}:{p['line']}: {field} is blank")
                    why = dict(p["fields"]).get("Why (incident)", "")
                    self.assertNotIn(NO_INCIDENT, why.lower(),
                                     f"{p['id']}: a principle needs a real incident")
                    rule = dict(p["fields"]).get("Rule", "")
                    self.assertTrue(rule.endswith("."), f"{p['id']}: Rule must end with a period")
                    self.assertNotIn(". ", rule, f"{p['id']}: Rule must be one sentence")
                    self.assertEqual(enforcer_problems(dict(p["fields"]).get("Enforced by", "")),
                                     [], f"{p['id']}: unknown Enforced by kind")

    def test_every_id_is_in_the_index_and_nowhere_else(self):
        index = read(PRINCIPLES / "README.md")
        listed = set(ID_IN_INDEX.findall(index))
        defined = set()
        for name in STAGE_FILES:
            self.assertIn(f"]({name})", index, f"index does not link {name}")
            defined |= {p["id"] for p in principles(read(PRINCIPLES / name))}
        self.assertEqual(sorted(defined - listed), [], "ids missing from the index")
        self.assertEqual(sorted(listed - defined), [], "index lists ids that do not exist")

    def test_every_enforcement_kind_is_defined_in_the_index(self):
        self.assertEqual(sorted(defined_kinds(read(PRINCIPLES / "README.md"))), sorted(ENFORCERS))

    def test_stated_totals_match_the_stage_files(self):
        total = sum(len(principles(read(PRINCIPLES / name))) for name in STAGE_FILES)
        for name in COUNT_FILES:
            with self.subTest(file=name):
                self.assertEqual(wrong_counts(read(ROOT / name), total), [])

    def test_no_internal_codes(self):
        for name in ("README.md",) + STAGE_FILES:
            with self.subTest(file=name):
                self.assertEqual(INTERNAL_CODE.findall(read(PRINCIPLES / name)), [])


class HelperTests(unittest.TestCase):
    """The checks above must be able to fail."""

    def test_enforcer_kinds(self):
        self.assertEqual(enforcer_problems("template + check_docs"), [])
        self.assertEqual(enforcer_problems("check_docs + contract hook (planned, v0.2)"), [])
        self.assertEqual(enforcer_problems("process"), ["process"])
        self.assertEqual(enforcer_problems("contract hook"), ["contract hook"])

    def test_wrong_total_fires(self):
        self.assertEqual(wrong_counts("The repository holds 21 principles.", 20), ["21 principles"])

    def test_right_total_passes(self):
        self.assertEqual(wrong_counts("20 principles in all.", 20), [])

    def test_text_without_a_total_passes(self):
        self.assertEqual(wrong_counts("The principles are listed below.", 20), [])

    def test_defined_kinds_reads_only_its_own_table(self):
        index = "## Enforcement kinds\n\n| Kind | Meaning |\n|---|---|\n| CI | x |\n\n## Index\n\n| Stage | y |\n"
        self.assertEqual(defined_kinds(index), ["CI"])

    def test_forbidden_hits_fire_case_insensitively(self):
        self.assertEqual(forbidden_hits("Built for ACMECORP.", ["AcmeCorp"]), ["AcmeCorp"])
        self.assertEqual(forbidden_hits("Built for Acme Corp.", ["AcmeCorp"]), [])

    def test_principles_parser_sees_fields(self):
        text = "### P3.1 Title\n- **Rule:** Do it.\n- **Enforced by:** CI\n## Next\n- **Rule:** x"
        items = principles(text)
        self.assertEqual(items[0]["fields"], [("Rule", "Do it."), ("Enforced by", "CI")])


class ForbiddenNamesTests(unittest.TestCase):
    def test_no_forbidden_names_in_tracked_files(self):
        raw = os.environ.get("ACP_FORBIDDEN_NAMES", "")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        if not names:
            self.skipTest("ACP_FORBIDDEN_NAMES is not set: the private-name scan did not run")
        self.assertEqual(forbidden_in_tracked_files(ROOT, names), [],
                         "private names found in tracked files")

    def test_scan_fails_on_a_tracked_probe_name(self):
        """The scan must fire on a tracked file and ignore untracked ones (probe name, not a real one)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "tracked.md").write_text("Built for ProbeCorp.\n", encoding="utf-8")
            (root / "untracked.md").write_text("ProbeCorp again.\n", encoding="utf-8")
            (root / "clean.md").write_text("Nothing to see.\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.md", "clean.md"], cwd=root, check=True)
            self.assertEqual(forbidden_in_tracked_files(root, ["probecorp"]),
                             ["tracked.md: probecorp"])
            self.assertEqual(forbidden_in_tracked_files(root, ["absentname"]), [])


if __name__ == "__main__":
    unittest.main()
