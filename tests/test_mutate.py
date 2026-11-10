"""Tests for scripts/mutate.py: rung 2 (proving that tests catch breakage) run from a script in this repository.

Each test builds a throwaway project in a temporary folder. The runner must never change that project's files.
"""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "agentic-principles" / "scripts" / "mutate.py"
sys.path.insert(0, str(SCRIPT.parent))

CALC = "def is_adult(age):\n    return age >= 18\n"
# Tests 20 and 10 only: flipping >= is caught, but changing 18 to 19 is not (nothing tests age 18).
WEAK_TEST = ("import unittest\nfrom calc import is_adult\n\n\nclass T(unittest.TestCase):\n"
             "    def test_it(self):\n        self.assertTrue(is_adult(20))\n        self.assertFalse(is_adult(10))\n")
LOOP = "def drain(n):\n    while n > 0:\n        n -= 1\n    return n\n"
LOOP_TEST = ("import unittest\nfrom loop import drain\n\n\nclass T(unittest.TestCase):\n"
             "    def test_it(self):\n        self.assertEqual(drain(3), 0)\n")
TEST_COMMAND = [sys.executable, "-m", "unittest", "-q"]


def make_project(files: dict[str, str]) -> Path:
    tmp = tempfile.mkdtemp()
    root = Path(tmp) / "proj"
    root.mkdir()
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return root


def digest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def run(root: Path, targets, timeout=30, extra=()):
    args = [sys.executable, str(SCRIPT), "--root", str(root), "--timeout", str(timeout), *extra]
    for t in targets:
        args += ["--target", t]
    return subprocess.run(args + ["--", *TEST_COMMAND], capture_output=True, text=True, timeout=600)


class MutantsTests(unittest.TestCase):
    def test_the_kinds_are_generated(self):
        import mutate
        kinds = {m.kind for m in mutate.mutants(CALC + "def f(x):\n    if x:\n        return 1\n    return 2\n")}
        self.assertEqual(kinds, {"flip comparison", "condition True", "condition False", "remove branch",
                                 "constant plus one"})

    def test_a_bool_is_not_a_number_to_change(self):
        import mutate
        self.assertFalse([m for m in mutate.mutants("FLAG = True\n") if m.kind == "constant plus one"])

    def test_every_mutant_differs_from_the_original_and_still_parses(self):
        import ast
        import mutate
        source = CALC + LOOP
        for m in mutate.mutants(source):
            with self.subTest(kind=m.kind, line=m.line):
                self.assertNotEqual(m.source, source)
                ast.parse(m.source)


class RunnerTests(unittest.TestCase):
    def test_a_weak_test_leaves_a_survivor_and_a_flip_is_killed(self):
        root = make_project({"calc.py": CALC, "test_calc.py": WEAK_TEST})
        result = run(root, ["calc.py"])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("constant plus one", result.stdout)
        self.assertRegex(result.stdout, r"killed\s*\|\s*[1-9]")
        self.assertIn("calc.py:2", result.stdout)

    def test_a_survivor_is_shown_with_the_original_line(self):
        """Found on the first real run: the line text was read from the rewritten copy, whose lines shift because
        ast.unparse drops comments and blank lines, so the report showed an empty or wrong line."""
        commented = "# a comment\n\n# another\n" + CALC
        root = make_project({"calc.py": commented, "test_calc.py": WEAK_TEST})
        result = run(root, ["calc.py"])
        self.assertIn("calc.py:5", result.stdout)
        self.assertIn("`return age >= 18`", result.stdout)

    def test_the_project_is_byte_identical_after_a_run(self):
        root = make_project({"calc.py": CALC, "test_calc.py": WEAK_TEST})
        before = digest(root)
        run(root, ["calc.py"])
        self.assertEqual(digest(root), before)

    def test_a_hanging_mutant_hits_the_timeout(self):
        root = make_project({"loop.py": LOOP, "test_loop.py": LOOP_TEST})
        result = run(root, ["loop.py"], timeout=5)
        self.assertRegex(result.stdout, r"timeout\s*\|\s*[1-9]", result.stdout + result.stderr)

    def test_all_killed_exits_zero(self):
        strong = WEAK_TEST.replace("self.assertFalse(is_adult(10))",
                                   "self.assertFalse(is_adult(10))\n        self.assertTrue(is_adult(18))\n"
                                   "        self.assertFalse(is_adult(17))")
        root = make_project({"calc.py": "def is_adult(age):\n    return age >= 18\n", "test_calc.py": strong})
        result = run(root, ["calc.py"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_failing_tests_before_any_mutation_stop_the_run(self):
        root = make_project({"calc.py": "def is_adult(age):\n    return age > 99\n", "test_calc.py": WEAK_TEST})
        result = run(root, ["calc.py"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("before any mutation", result.stderr)

    def test_a_target_outside_the_project_is_refused(self):
        root = make_project({"calc.py": CALC, "test_calc.py": WEAK_TEST})
        result = run(root, ["../elsewhere.py"])
        self.assertEqual(result.returncode, 2)

    def test_no_test_command_is_a_usage_error(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--target", "x.py"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
