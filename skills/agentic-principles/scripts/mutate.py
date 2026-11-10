"""Mutation runner: rung 2 of the test ladder, proving that the tests catch breakage.

Usage: python mutate.py --target <file.py> [--target <file.py> ...] [--root <project folder>] [--timeout SECONDS]
                        -- <test command ...>
Example: python mutate.py --target src/app.py --timeout 60 -- python -m unittest -q

A mutation is one small deliberate change to the code. For each one the runner copies the project into a throwaway
folder, applies the change there, and runs the test command. The mutant is
  killed     the tests failed: they noticed the change (good)
  survived   the tests still passed: nothing tests that behaviour (a gap to look at)
  timeout    the tests ran longer than --timeout seconds (counted apart, never as killed)
The project itself is never changed: every run works on a copy in a temporary folder.

Mutation kinds (Python files, read with the standard library's ast module):
  flip comparison     == and !=, < and >=, <= and >, in and not in, is and is not
  condition True      the test of an if or while replaced by True
  condition False     the test of an if or while replaced by False
  remove branch       the body of an if replaced by pass
  constant plus one   an integer constant n replaced by n + 1 (True and False are left alone)
A mutated file is written back with ast.unparse, so its comments and layout differ on the copy; behaviour is what
the tests see.

Before any mutation the tests run once on an unchanged copy; if they fail there, the run stops.
Output: a results table (killed, survived, timeout) and one line per survivor and timeout, as file:line, kind and
the changed line, ready to paste into RESULTS.md.
Exit codes: 0 every mutant killed, 1 at least one survivor or timeout, 2 the run cannot start (usage, a target
outside the project or not Python, the tests failing before any mutation).
Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import copy
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

FLIPS = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.LtE: ast.Gt, ast.Gt: ast.LtE,
         ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache"}


@dataclass
class Mutant:
    kind: str
    line: int
    source: str          # the whole mutated file


def _changes(tree: ast.AST):
    """(index in ast.walk order, kind, function that changes that node in place) for every mutation."""
    for index, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare):
            for position, op in enumerate(node.ops):
                if type(op) in FLIPS:
                    yield index, "flip comparison", (lambda n, p=position: n.ops.__setitem__(p, FLIPS[type(n.ops[p])]()))
        if isinstance(node, (ast.If, ast.While)):
            yield index, "condition True", lambda n: setattr(n, "test", ast.Constant(True))
            yield index, "condition False", lambda n: setattr(n, "test", ast.Constant(False))
        if isinstance(node, ast.If) and not (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)):
            yield index, "remove branch", lambda n: setattr(n, "body", [ast.Pass()])
        if isinstance(node, ast.Constant) and type(node.value) is int:
            yield index, "constant plus one", lambda n: setattr(n, "value", n.value + 1)


def mutants(source: str) -> list[Mutant]:
    """Every single-change mutant of a Python source text."""
    tree = ast.parse(source)
    out = []
    for index, kind, change in list(_changes(tree)):
        clone = copy.deepcopy(tree)
        node = next(n for i, n in enumerate(ast.walk(clone)) if i == index)
        change(node)
        ast.fix_missing_locations(clone)
        text = ast.unparse(clone) + "\n"
        if text != source:
            out.append(Mutant(kind, getattr(node, "lineno", 0), text))
    return out


def _copy_project(root: Path, into: Path) -> Path:
    target = into / root.name
    shutil.copytree(root, target, ignore=lambda folder, names: [n for n in names if n in SKIP_DIRS])
    return target


def _run_tests(folder: Path, command: list[str], timeout: float) -> str:
    try:
        result = subprocess.run(command, cwd=folder, capture_output=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "timeout"
    return "survived" if result.returncode == 0 else "killed"


def _target_path(root: Path, rel: str) -> Path | None:
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.suffix != ".py":
        return None
    return path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command = args[args.index("--") + 1:] if "--" in args else []
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", action="append", required=True, help="a Python file to mutate (repeatable)")
    parser.add_argument("--root", default=".", help="the project folder (default: the current folder)")
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per test run (default 120)")
    try:
        opts = parser.parse_args(args[:args.index("--")] if "--" in args else args)
    except SystemExit:
        return 2
    if not command:
        print("mutate.py: give the test command after '--', for example: -- python -m unittest -q", file=sys.stderr)
        return 2
    root = Path(opts.root)
    if not root.is_dir():
        print(f"mutate.py: not a folder: {root}", file=sys.stderr)
        return 2
    targets = []
    for rel in opts.target:
        path = _target_path(root, rel)
        if path is None:
            print(f"mutate.py: {rel} is not a Python file inside {root}", file=sys.stderr)
            return 2
        targets.append(path.relative_to(root.resolve()).as_posix())

    counts = {"killed": 0, "survived": 0, "timeout": 0}
    gaps: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        work = _copy_project(root.resolve(), Path(tmp))
        if _run_tests(work, command, opts.timeout) != "survived":
            print("mutate.py: the tests do not pass before any mutation; fix them first", file=sys.stderr)
            return 2
        for rel in targets:
            original = (work / rel).read_text(encoding="utf-8")
            lines = original.splitlines()
            for m in mutants(original):
                (work / rel).write_text(m.source, encoding="utf-8")
                outcome = _run_tests(work, command, opts.timeout)
                counts[outcome] += 1
                if outcome != "killed":
                    # m.line counts lines of the original file; the rewritten copy has shifted lines.
                    shown = lines[m.line - 1].strip() if 0 < m.line <= len(lines) else ""
                    gaps.append(f"| {outcome} | {rel}:{m.line} | {m.kind} | `{shown}` |")
            (work / rel).write_text(original, encoding="utf-8")

    total = sum(counts.values())
    print(f"Mutation run: {total} mutants of {', '.join(targets)}; test command: {' '.join(command)}\n")
    print("| Outcome | Count |\n|---|---|")
    for outcome in ("killed", "survived", "timeout"):
        print(f"| {outcome} | {counts[outcome]} |")
    if gaps:
        print("\nNot killed (each needs a test, or a written reason it cannot matter):\n")
        print("| Outcome | Where | Kind | Changed line |\n|---|---|---|---|")
        print("\n".join(gaps))
    return 0 if not gaps else 1


if __name__ == "__main__":
    sys.exit(main())
