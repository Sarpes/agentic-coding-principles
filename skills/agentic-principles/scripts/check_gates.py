"""Stage gate: checks that each stage marked done in STAGES.md has the evidence its gate needs.

Usage: python check_gates.py [--go-live] [project folder]   (default: the current directory)
--go-live prints the detected traits and the ids GO-LIVE.md must cover, and exits 0.
Exit codes: 0 no problems, 1 problems found (printed as FILE:LINE: message), 2 the folder cannot be checked
(more than one argument, not a directory, not the top of a git repository, or a shallow clone).
Line numbers are 1-based lines of the original file; 0 means the problem concerns the whole file.
Notes (for example the list of open overrides) go to stderr and never change the exit code.

This script is copied alone into projects: it uses the standard library only and imports nothing from the
repository it ships in. Git is run through the `git` command.

Layout (one file on purpose, so it can be copied alone; search for the section banner):
  text helpers      comment/fence blanking, table rows, UTF-8 decoding
  git               tracked files, first commit of a file, ancestry
  STAGES.md         parse_stages and its table parser
  evidence          the REQUIRED table, evidence items, per-file content rules
  stage checks      stage_problems: evidence, ordering, overrides, adoption
  OVERRIDES.md      parse_overrides and override_problems
  architecture      file map, dependency table, test table and attack list checks, manifest readers, their timing
  traits and go-live  trait detection, the Small size check, the checklist file, GO-LIVE.md rows
  OWNERSHIP.md      explain-back (stage 5), full round, hand-changed commit and re-check (stage 6)
  stage wiring      go_live_ownership_problems: which of the above binds at which stage
  command          check_project and main
"""
from __future__ import annotations

import fnmatch
import json
import posixpath
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import NamedTuple

__version__ = "0.2.0"

STAGE_NAMES = ("0 Intake", "1 Design", "2 Plan", "3 Build", "4 Verify", "5 Ship", "6 Own", "7 Retro")
STATUSES = ("open", "passed", "overridden", "adopted", "reopened")
CLOSED = ("passed", "overridden", "adopted")
SIZES = ("small", "full")
METHODS = ("normal", "sub-agent")
STAGES_FILE = "STAGES.md"
OVERRIDES_FILE = "OVERRIDES.md"
EXAMPLE_MARKER = "(EXAMPLE)"
MAX_ADOPTED_AT = 5
# File types that count as source code: for the adoption check here and for the size and hand-change checks later.
SOURCE_EXTENSIONS = (".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".swift",
                     ".c", ".cpp", ".h", ".rb", ".php", ".cs", ".sh", ".ps1")

TRUST_LIMIT = (
    "check_gates.py trust limit: it verifies that evidence exists (a named file is present, a named commit is "
    "real, a table row is filled). It cannot tell whether the owner really approved something or wrote a commit, "
    "because the owner and the agent share one git identity, and it cannot judge the quality of written prose. "
    "A green result is not proof that a person reviewed the work.")


class Problem(NamedTuple):
    file: str
    line: int
    message: str


class GateError(Exception):
    """The folder cannot be checked at all; the command exits with code 2."""


class Row(NamedTuple):
    line: int
    name: str
    status: str
    evidence: str
    override: str


@dataclass
class Stages:
    size: str | None = None
    size_line: int = 0
    method: str | None = None
    adopted_at: int | None = None
    adopted_at_line: int = 0
    traits: set[str] | None = None
    rows: dict[int, Row] = field(default_factory=dict)
    errors: list[tuple[int, str]] = field(default_factory=list)      # (line, message), turned into Problems later


class Override(NamedTuple):
    status: str
    stage: str
    reconfirmed: str


class Need(NamedTuple):
    """One thing a stage's evidence must contain."""
    kind: str                       # "file" (exact path), "under" (any file below a folder), "commit"
    value: str
    label: str                      # what the owner is told is missing
    exclude: tuple[str, ...] = ()   # for "under": folders that do not count


# ------------------------------------------------------------------ text helpers

def normalise(text: str) -> str:
    """Drop a byte-order mark and turn CRLF into LF."""
    return text.lstrip("﻿").replace("\r\n", "\n")


FENCE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")
FIELD = re.compile(r"^- \*\*(.+?):\*\*[ \t]*(.*)$")
PLACEHOLDER = re.compile(r"(none|n/?a|tbd|todo|-|\.\.\.|…)?\.?", re.I)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
REQ_ID = re.compile(r"\bREQ-\d+\b")
ATK_ID = re.compile(r"\bATK-\d+\b")


def clean_lines(text: str) -> list[str]:
    """Lines with HTML comments and fenced code blocks blanked, so line numbers stay true."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group().count("\n"), normalise(text), flags=re.S)
    lines = text.split("\n")
    opened = None                                         # backtick count of the open fence
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if opened is None:
            if m:
                opened = len(m.group(1))
                lines[i] = ""
        else:
            if m and len(m.group(1)) >= opened and not m.group(2).strip():
                opened = None
            lines[i] = ""
    return lines


def split_row(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", inner)]


def is_alignment_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", c) for c in cells)


def decode(data: bytes, name: str):
    """(text, None), or (None, Problem) for bytes that are not UTF-8: a problem in the file, not a crash."""
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError as error:
        line = data[:error.start].count(b"\n") + 1
        return None, Problem(name, line, f"not valid UTF-8 (byte 0x{data[error.start]:02x}); save the file as UTF-8")


# ------------------------------------------------------------------------- git

def git(root, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(root), *args],
                              capture_output=True, stdin=subprocess.DEVNULL)
    except OSError as error:
        raise GateError(f"cannot run git: {error}") from error


def git_text(root, *args: str) -> str | None:
    """Standard output of a git command as text, or None when the command fails."""
    result = git(root, *args)
    return normalise(result.stdout.decode("utf-8", "replace")) if result.returncode == 0 else None


def tracked_files(root) -> list[str]:
    """Every file git tracks, as paths with forward slashes."""
    result = git(root, "ls-files", "-z")
    if result.returncode != 0:
        return []
    return [name.decode("utf-8", "replace") for name in result.stdout.split(b"\0") if name]


def require_checkable_repo(root: Path) -> None:
    top = git_text(root, "rev-parse", "--show-toplevel")
    if top is None:
        raise GateError(f"not a git repository: {root}")
    try:
        same = Path(top.strip()).samefile(root)
    except OSError:
        same = False
    if not same:
        raise GateError(f"{root} is inside a git repository whose top folder is {top.strip()}; "
                        "run the check on that top folder")
    if (git_text(root, "rev-parse", "--is-shallow-repository") or "").strip() == "true":
        raise GateError("this is a shallow clone: commit evidence cannot be verified without full history "
                        "(run: git fetch --unshallow)")


def first_commit_of(root, name: str) -> str | None:
    """The commit that added `name` in the current cycle: the newest add, because a new cycle adds it again."""
    out = git_text(root, "log", "--diff-filter=A", "--format=%H", "--", name)
    lines = out.split() if out else []
    return lines[0] if lines else None


def resolve_commit(root, ref: str) -> str | None:
    out = git_text(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return out.strip() if out else None


def is_ancestor(root, older: str, newer: str) -> bool:
    return git(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def commit_is_after(root, first: str, commit: str) -> bool:
    """True for a commit strictly after `first` on the same line of history."""
    a, b = resolve_commit(root, first), resolve_commit(root, commit)
    return bool(a and b and a != b and is_ancestor(root, a, b))


# ------------------------------------------------------------------- STAGES.md

def parse_stages(text: str) -> Stages:
    lines = clean_lines(text)
    stages = Stages()
    seen: set[str] = set()
    table: list[tuple[int, str]] = []
    header = re.compile(r"^(Size|Method|Adopted-at|Traits):[ \t]*(.*?)[ \t]*$")
    for number, line in enumerate(lines, start=1):
        m = header.match(line)
        if not m:
            if line.lstrip().startswith("|"):
                table.append((number, line))
            continue
        label, value = m.groups()
        if label in seen:
            stages.errors.append((number, f"'{label}:' appears twice"))
            continue
        seen.add(label)
        if label == "Size":
            stages.size_line = number
            if value in SIZES:
                stages.size = value
            else:
                stages.errors.append((number, f"Size must be one of: {', '.join(SIZES)} (found '{value}')"))
        elif label == "Method":
            if value in METHODS:
                stages.method = value
            else:
                stages.errors.append((number, f"Method must be one of: {', '.join(METHODS)} (found '{value}')"))
        elif label == "Adopted-at":
            stages.adopted_at_line = number
            if value.isdigit():
                stages.adopted_at = int(value)
            else:
                stages.errors.append((number, f"Adopted-at must be a stage number (found '{value}')"))
        else:
            names = {t.strip().lower() for t in value.split(",")} - {""}
            stages.traits = set() if names == {"none"} else names
    for label, found in (("Size", stages.size), ("Method", stages.method)):
        if found is None and label not in seen:
            options = " or ".join(f"'{label}: {o}'" for o in (SIZES if label == "Size" else METHODS))
            stages.errors.append((0, f"missing line {options}"))
    _parse_stage_table(stages, table)
    return stages


def _parse_stage_table(stages: Stages, table: list[tuple[int, str]]) -> None:
    expected = ["Stage", "Status", "Evidence", "Override"]
    if not table:
        stages.errors.append((0, "no stage table found (columns: " + " | ".join(expected) + ")"))
        return
    head_line, head = table[0]
    if [c.lower() for c in split_row(head)] != [c.lower() for c in expected]:
        stages.errors.append((head_line, "table columns must be exactly: " + " | ".join(expected)))
        return
    data = table[1:]
    if data and is_alignment_row(split_row(data[0][1])):
        data = data[1:]
    by_name = {name.casefold(): n for n, name in enumerate(STAGE_NAMES)}
    for number, line in data:
        cells = split_row(line)
        if len(cells) != len(expected):
            stages.errors.append((number, f"row has {len(cells)} cells; expected {len(expected)}"))
            continue
        name_cell, status, evidence, override = cells
        stage = by_name.get(" ".join(name_cell.split()).casefold())
        if stage is None:
            stages.errors.append((number, f"unknown stage '{name_cell}'; expected one of: {', '.join(STAGE_NAMES)}"))
            continue
        if stage in stages.rows:
            stages.errors.append((number, f"stage '{STAGE_NAMES[stage]}' appears twice"))
            continue
        if status not in STATUSES:
            stages.errors.append((number, f"{STAGE_NAMES[stage]}: Status '{status}' must be one of: "
                                          + ", ".join(STATUSES)))
        stages.rows[stage] = Row(number, STAGE_NAMES[stage], status, evidence, override)
    for stage, name in enumerate(STAGE_NAMES):
        if stage not in stages.rows and not any(f"'{name}'" in m for _, m in stages.errors):
            stages.errors.append((0, f"stage '{name}' has no row"))


# -------------------------------------------------------------------- evidence

_REQUIREMENTS = (Need("file", "REQUIREMENTS.md", "REQUIREMENTS.md"), Need("file", "ATTACKS.md", "ATTACKS.md"))
_DECISIONS = Need("file", "DECISIONS.md", "DECISIONS.md")
_DESIGN = Need("under", "docs/", "a design file under docs/ (not docs/plans/)", ("docs/plans/",))
_BUILD = (Need("commit", "", "a commit made after STAGES.md was first committed"),
          Need("file", "BUILD-LEDGER.md", "BUILD-LEDGER.md"))
_ARCHITECTURE = Need("file", "ARCHITECTURE.md", "ARCHITECTURE.md")
_RESULTS = Need("file", "RESULTS.md", "RESULTS.md")
_OWNERSHIP = Need("file", "OWNERSHIP.md", "OWNERSHIP.md")
_AI_LOG = Need("file", "AI-Agents.md", "AI-Agents.md")

# Design section 11: required evidence per stage and size. The GO-LIVE.md requirement joins stage 5 with the traits.
REQUIRED: dict[tuple[int, str], tuple[Need, ...]] = {
    (0, "small"): _REQUIREMENTS,
    (0, "full"): _REQUIREMENTS,
    (1, "small"): (_DECISIONS,),
    (1, "full"): (_DECISIONS, _DESIGN),
    (2, "small"): (Need("file", "PLAN.md", "PLAN.md"),),
    (2, "full"): (Need("under", "docs/plans/", "a plan file in docs/plans/"),),
    (3, "small"): _BUILD,
    (3, "full"): _BUILD,
    (4, "small"): (_ARCHITECTURE,),
    (4, "full"): (_ARCHITECTURE, _RESULTS),
    (5, "small"): (_OWNERSHIP,),
    (5, "full"): (_OWNERSHIP,),
    (6, "small"): (_OWNERSHIP,),
    (6, "full"): (_OWNERSHIP,),
    (7, "small"): (_AI_LOG,),
    (7, "full"): (_AI_LOG,),
}


def parse_evidence(cell: str):
    """(items, errors): items are (kind, value) pairs from a cell like 'file:a.md, commit:abc1234'."""
    items, errors = [], []
    if cell.strip() in ("", "-"):
        return items, errors
    for part in cell.split(","):
        part = part.strip()
        kind, _, value = part.partition(":")
        if kind in ("file", "commit") and value.strip():
            items.append((kind, value.strip()))
        else:
            errors.append(f"evidence item '{part}' must be written file:<path> or commit:<hash>")
    return items, errors


def norm_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))


def read_evidence_file(root: Path, rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    text, problem = decode(path.read_bytes(), rel)
    return None if problem else normalise(text)               # not UTF-8: reported by stage_problems, never judged


def evidence_item_problems(kind: str, value: str, root: Path, tracked: set[str]) -> list[str]:
    """Why one evidence item is not acceptable (empty list when it is)."""
    if kind == "commit":
        if not re.fullmatch("[0-9a-f]{7,40}", value):
            return [f"commit:{value} is not a hexadecimal hash (7 to 40 characters from 0-9 and a-f)"]
        resolved = resolve_commit(root, value)
        if not (resolved and is_ancestor(root, resolved, "HEAD")):
            return [f"commit:{value} is not in the history of the current branch"]
        return []
    rel = norm_path(value)
    if rel.casefold() in (STAGES_FILE.casefold(), OVERRIDES_FILE.casefold()):
        return [f"file:{value}: {rel} is the gate's own record and cannot be evidence"]
    path = root / rel
    try:
        inside = path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        inside = False
    if not inside:
        return [f"file:{value} points outside the project"]
    if path.is_dir():
        return [f"file:{value} is a folder; name a file"]
    if rel not in tracked:
        if not path.is_file():
            return [f"file:{value} does not exist"]
        return [f"file:{value} is not tracked by git; add and commit it"]
    if not path.is_file():
        return [f"file:{value} is tracked but missing from the working folder"]
    text = path.read_bytes().decode("utf-8", "replace")
    if not text.strip():
        return [f"file:{value} is empty"]
    if EXAMPLE_MARKER in text:
        return [f"file:{value} still contains the template marker {EXAMPLE_MARKER}; replace the worked example"]
    return []


def req_problems(text: str) -> list[str]:
    if any(REQ_ID.search(line) for line in clean_lines(text)):
        return []
    return ["no REQ-n identifier found (for example REQ-1); the acceptance criteria are not stated"]


def decisions_entry_problems(text: str) -> list[str]:
    if any(re.match(r"### D\d+\.", line) for line in clean_lines(text)):
        return []
    return ["no decision entry found (### D1. ...)"]


def section_lines(text: str, heading: str) -> list[str] | None:
    """Cleaned lines under `## heading`, up to the next heading of level 1 or 2; None when absent."""
    lines = clean_lines(text)
    for i, line in enumerate(lines):
        if re.fullmatch(rf"## {re.escape(heading)}[ \t]*", line):
            body = []
            for later in lines[i + 1:]:
                if re.match(r"#{1,2} ", later):
                    break
                body.append(later)
            return body
    return None


def ledger_problems(text: str) -> list[str]:
    body = section_lines(text, "Reviews")
    if body is None:
        return ["no '## Reviews' section; record each review there (Task | Reviewer | Result)"]
    rows = [split_row(line) for line in body if line.lstrip().startswith("|")]
    if not rows or [c.lower() for c in rows[0]] != ["task", "reviewer", "result"]:
        return ["the Reviews table must have the columns Task | Reviewer | Result (one row per review)"]
    data = [r for r in rows[1:] if not is_alignment_row(r)]
    if not any(len(r) == 3 and all(r) for r in data):
        return ["the Reviews table has no review row with Task, Reviewer and Result filled in"]
    return []


def retro_problems(text: str) -> list[str]:
    body = section_lines(text, "Retro")
    if body is None:
        return ["no '## Retro' section; write what each 'where the AI was wrong' entry became"]
    if not any(line.strip() for line in body):
        return ["the '## Retro' section is empty"]
    return []


# A rule runs only at the stage that needs the file, so a file cited elsewhere is not judged by the wrong rule.
CONTENT_RULES = {
    (0, "REQUIREMENTS.md"): req_problems,
    (1, "DECISIONS.md"): decisions_entry_problems,
    (3, "BUILD-LEDGER.md"): ledger_problems,
    (7, "AI-Agents.md"): retro_problems,
}


def evidence_content_problems(stage: int, size, root, tracked, row: Row, stages_first_commit: str | None,
                              file: str = STAGES_FILE) -> list[Problem]:
    """What a stage's evidence must contain, and whether the named files say it."""
    root = Path(root)
    name = STAGE_NAMES[stage]
    items, _ = parse_evidence(row.evidence)
    files = [norm_path(v) for k, v in items if k == "file"]
    commits = [v for k, v in items if k == "commit"]
    problems: list[Problem] = []
    for need in REQUIRED.get((stage, size), ()):
        if need.kind == "file" and need.value not in files:
            problems.append(Problem(file, row.line, f"{name}: the evidence must include 'file:{need.value}'"))
        elif need.kind == "under" and not any(
                f.startswith(need.value) and not f.startswith(need.exclude) for f in files):
            problems.append(Problem(file, row.line, f"{name}: the evidence must include {need.label}"))
        elif need.kind == "commit":
            problems += _commit_after_problems(name, root, commits, stages_first_commit, row, file)
    tracked_set = set(tracked)
    for rel in files:
        rule = CONTENT_RULES.get((stage, rel))
        text = read_evidence_file(root, rel) if rule and rel in tracked_set else None
        if text is not None:
            problems += [Problem(rel, 0, f"{name}: {message}") for message in rule(text)]
    return problems


def _commit_after_problems(name, root, commits, first, row, file) -> list[Problem]:
    if not commits:
        return [Problem(file, row.line, f"{name}: the evidence must include a 'commit:<hash>' made after "
                                        f"{STAGES_FILE} was first committed")]
    if first is None:
        return [Problem(file, row.line, f"{name}: {STAGES_FILE} is not committed yet, so no commit can come after "
                                        "it; commit it first, then build")]
    if not any(commit_is_after(root, first, c) for c in commits):
        return [Problem(file, row.line, f"{name}: no listed commit was made after {STAGES_FILE} was first "
                                        "committed; the setup commit does not count")]
    return []


# ---------------------------------------------------------------- stage checks

def stage_problems(text: str, root, tracked, overrides: dict, file: str = STAGES_FILE) -> list[Problem]:
    root = Path(root)
    stages = parse_stages(text)
    problems = [Problem(file, line, message) for line, message in stages.errors]
    tracked_set = set(tracked)
    memo: list = []

    def first_commit():
        if not memo:
            memo.append(first_commit_of(root, file))
        return memo[0]

    for n in sorted(stages.rows):
        row = stages.rows[n]
        if row.status in CLOSED:
            earlier = [m for m in range(n) if m in stages.rows and stages.rows[m].status == "open"]
            if earlier:
                problems.append(Problem(file, row.line, f"{row.name} is {row.status} but the earlier stage "
                                                        f"{STAGE_NAMES[earlier[0]]} is still open"))
        if row.status == "passed":
            problems += _passed_problems(n, stages, row, root, tracked_set, tracked, first_commit, file)
        elif row.status == "overridden":
            problems += _override_cell_problems(row, overrides, file)
        elif row.status == "reopened" and n != 6:
            problems.append(Problem(file, row.line, f"{row.name}: 'reopened' is only allowed for stage 6 Own"))
    problems += _adoption_problems(stages, root, first_commit, file)
    return problems


def _passed_problems(n, stages, row, root, tracked_set, tracked, first_commit, file) -> list[Problem]:
    items, shape_errors = parse_evidence(row.evidence)
    if not items and not shape_errors:
        return [Problem(file, row.line, f"{row.name} is passed but names no evidence "
                                        "(write file:<path> or commit:<hash>)")]
    problems = [Problem(file, row.line, f"{row.name}: {message}") for message in shape_errors]
    for kind, value in items:
        found = evidence_item_problems(kind, value, root, tracked_set)
        problems += [Problem(file, row.line, f"{row.name}: {message}") for message in found]
        if kind == "file" and not found:                     # a usable file: its bytes must be UTF-8
            rel = norm_path(value)
            problem = decode((root / rel).read_bytes(), rel)[1]
            if problem:
                problems.append(problem)
    first = first_commit() if n == 3 else None
    problems += evidence_content_problems(n, stages.size, root, tracked, row, first, file)
    return problems


def _override_cell_problems(row: Row, overrides: dict, file: str) -> list[Problem]:
    ident = row.override.strip()
    if not re.fullmatch(r"O\d+", ident):
        return [Problem(file, row.line, f"{row.name} is overridden but the Override column does not name an "
                                        "override (for example O1)")]
    found = overrides.get(ident)
    if found is None:
        return [Problem(file, row.line, f"{row.name} is overridden by {ident}, which is not in OVERRIDES.md")]
    if found.status != "open":
        return [Problem(file, row.line, f"{row.name}: override {ident} is {found.status or 'not open'}; an "
                                        "override only counts while it is open")]
    match = re.match(r"\s*([0-7])(?!\d)", found.stage)         # only stages 0-7 exist; anything else is no match
    if not match or STAGE_NAMES[int(match.group(1))] != row.name:
        return [Problem(file, row.line, f"{row.name}: override {ident} is for stage '{found.stage}', "
                                        "not for this stage")]
    return []


def _adoption_problems(stages: Stages, root: Path, first_commit, file: str) -> list[Problem]:
    adopted = [r for r in stages.rows.values() if r.status == "adopted"]
    n = stages.adopted_at
    problems = []
    if n is not None and n > MAX_ADOPTED_AT:
        problems.append(Problem(file, stages.adopted_at_line, f"Adopted-at: {n} is too high; it may be at most "
                                f"{MAX_ADOPTED_AT}, so that 5 Ship and 6 Own are always done"))
    for r in adopted:
        if n is None:
            problems.append(Problem(file, r.line, f"{r.name} is adopted but there is no 'Adopted-at: N' line"))
        elif STAGE_NAMES.index(r.name) >= n:
            problems.append(Problem(file, r.line, f"{r.name} is adopted but only stages below Adopted-at: {n} "
                                                  "may be adopted"))
    if not adopted or n is None:
        return problems
    first = first_commit()
    if first is None:
        return problems + [Problem(file, stages.adopted_at_line, f"{file} is not committed yet; commit it so "
                                   "the Adopted-at line can be checked against its first commit")]
    old = git_text(root, "show", f"{first}:{file}")
    if parse_stages(old or "").adopted_at != n:
        problems.append(Problem(file, stages.adopted_at_line, "the Adopted-at line is not the one in the first "
                                f"commit of {file}; it must be there from the start and never change"))
    before = git_text(root, "ls-tree", "-r", "--name-only", f"{first}^")
    if not any(name.lower().endswith(SOURCE_EXTENSIONS) for name in (before or "").split("\n")):
        problems.append(Problem(file, stages.adopted_at_line, "no source files in the commit before "
                                f"{file} first appeared, so this looks like a new project; adoption is for "
                                "projects that already have source"))
    return problems


# ----------------------------------------------------------------- OVERRIDES.md

OVERRIDE_FIELDS = ("Date", "Stage", "What was skipped", "Why", "Risk accepted", "How to close", "Status",
                   "Closing evidence", "Re-confirmed for release")
TEXT_FIELDS = ("What was skipped", "Why", "Risk accepted", "How to close")


def _override_entries(lines: list[str]):
    """(number, heading line, {label: (value, line)}) for each '### O<n>. title'; a body runs to the next heading."""
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"### O(\d+)\. ", line)
        if not m:
            continue
        fields: dict[str, tuple[str, int]] = {}
        for j in range(i + 1, len(lines)):
            if re.match(r"#{1,3} ", lines[j]):
                break
            f = FIELD.match(lines[j])
            if f:
                fields[f.group(1).strip()] = (f.group(2).strip(), j + 1)
        out.append((int(m.group(1)), i + 1, fields))
    return out


def parse_overrides(text: str) -> dict[str, Override]:
    result = {}
    for n, _, fields in _override_entries(clean_lines(text)):
        get = lambda label: fields.get(label, ("", 0))[0]          # noqa: E731
        result[f"O{n}"] = Override(get("Status").lower(), get("Stage"), get("Re-confirmed for release"))
    return result


def _history_ids(root, file: str) -> set[int]:
    """Override numbers present in any committed version of the file reachable from HEAD."""
    ids: set[int] = set()
    log = git_text(root, "log", "--full-history", "--format=%H", "--", file) or ""
    for commit in log.split():
        old = git_text(root, "show", f"{commit}:{file}")
        if old:
            ids |= {n for n, _, _ in _override_entries(clean_lines(old))}
    return ids


def override_problems(text, root, stages, file: str = OVERRIDES_FILE) -> list[Problem]:
    """Problems in OVERRIDES.md; `text` is None when the file is absent from the working folder."""
    history = _history_ids(root, file)
    if text is None:
        if history:
            return [Problem(file, 0, f"{file} vanished: earlier commits hold it, but it is gone; entries are "
                                     "never deleted")]
        return []
    lines = clean_lines(text)
    entries = _override_entries(lines)
    problems = []
    for i, line in enumerate(lines):
        if re.match(r"#{1,6}\s*O\d+", line) and not re.match(r"### O\d+\. \S", line):
            problems.append(Problem(file, i + 1, f"heading '{line.strip()}' is not in the form '### O<number>. <title>'"))
    for position, (n, heading_line, _) in enumerate(entries):
        if n != position + 1:
            listed = ", ".join(f"O{x}" for x, _, _ in entries)
            problems.append(Problem(file, heading_line, f"numbering is {listed}; expected O1..O{len(entries)} in order"))
            break
    for n, heading_line, fields in entries:
        problems += _entry_problems(n, heading_line, fields, file)
    present = {n for n, _, _ in entries}
    problems += [Problem(file, 0, f"O{n} vanished: it was in an earlier commit but is not in the file now; "
                                  "entries are never deleted (mark it closed instead)")
                 for n in sorted(history - present)]
    ship = stages.rows.get(5) if stages is not None else None
    if ship is not None and ship.status in ("passed", "overridden"):
        for n, heading_line, fields in entries:
            status = fields.get("Status", ("", 0))[0].lower()
            confirmed = fields.get("Re-confirmed for release", ("", 0))[0]
            if status == "open" and not ISO_DATE.fullmatch(confirmed):
                problems.append(Problem(file, heading_line, f"O{n} is still open at stage 5 Ship ({ship.status}); "
                                        "'Re-confirmed for release' must hold the date the owner re-confirmed it"))
    return problems


def _entry_problems(n: int, heading_line: int, fields: dict, file: str) -> list[Problem]:
    problems = []
    for label in OVERRIDE_FIELDS:
        if label not in fields:
            problems.append(Problem(file, heading_line, f"O{n}: missing '- **{label}:**'"))
        elif not fields[label][0]:
            problems.append(Problem(file, fields[label][1], f"O{n}: '{label}' is empty"))
        elif label in TEXT_FIELDS and PLACEHOLDER.fullmatch(fields[label][0]):
            problems.append(Problem(file, fields[label][1], f"O{n}: '{label}' is a placeholder; say what it is"))
    value = lambda label: fields.get(label, ("", 0))[0]              # noqa: E731
    line = lambda label: fields.get(label, (0, heading_line))[1]     # noqa: E731
    checks = (
        ("Date", value("Date") and not _is_date(value("Date")), "must be a date like 2026-11-09"),
        ("Stage", value("Stage") and not re.match(r"[0-7]\b", value("Stage")),
         "must name a stage, for example '3 Build'"),
        ("Status", value("Status") and value("Status") not in ("open", "closed"), "must be open or closed"),
        ("Re-confirmed for release",
         value("Re-confirmed for release") not in ("", "-") and not _is_date(value("Re-confirmed for release")),
         "must be '-' or a date like 2026-11-09"),
    )
    for label, bad, rule in checks:
        if bad:
            problems.append(Problem(file, line(label), f"O{n}: {label} '{value(label)}' {rule}"))
    if value("Status") == "closed" and value("Closing evidence") in ("", "-"):
        problems.append(Problem(file, line("Closing evidence"), f"O{n}: Closing evidence is '-' but the override "
                                                                "is closed; say how it was closed"))
    return problems


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return bool(ISO_DATE.fullmatch(value))


# ------------------------------------------------------ architecture and attacks

ARCHITECTURE_FILE = "ARCHITECTURE.md"
ATTACKS_FILE = "ATTACKS.md"
REQUIREMENTS_FILE = "REQUIREMENTS.md"
MAX_FOLDER_FILES = 10
ATTACK_MINIMUM = {"small": 3, "full": 5}
COMPONENT_COLUMNS = ["Component", "What it does"]
MAP_COLUMNS = ["Path", "What it does"]
TEST_COLUMNS = ["Part", "1 Written first", "2 Catches breakage", "3 Input range", "4 Real integration",
                "5 Deliberate failure"]
DEP_COLUMNS = ["Name", "Version", "Why it is here", "What breaks without it"]
ATTACK_COLUMNS = ["ID", "Attack", "Rung", "Drafted by"]
BULK = re.compile(r"\(bulk:[ \t]*\S[^)]*\)", re.I)
OVERRIDE_LINE = re.compile(r"^Override:[ \t]*(O\d+)\b", re.M)
UNREADABLE_MANIFESTS = ("go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "composer.json",
                        "environment.yml", "setup.py", "Pipfile")
PINNED_NPM = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]*)?")


def _section(text: str, heading: str):
    """(heading line, [(line number, cleaned line)]) for `## heading`, up to the next heading of level 1 or 2."""
    lines = clean_lines(text)
    for i, line in enumerate(lines):
        if re.fullmatch(rf"## {re.escape(heading)}[ \t]*", line):
            body = []
            for j in range(i + 1, len(lines)):
                if re.match(r"#{1,2} ", lines[j]):
                    break
                body.append((j + 1, lines[j]))
            return i + 1, body
    return None


def _table(anchor: int, body, columns: list[str]):
    """(rows, errors): rows are (line, cells) under a header that must match `columns`; errors are (line, message)."""
    lines = [(n, line) for n, line in body if line.lstrip().startswith("|")]
    wanted = " | ".join(columns)
    if not lines:
        return [], [(anchor, f"no table found (columns: {wanted})")]
    head_line, head = lines[0]
    if [c.lower() for c in split_row(head)] != [c.lower() for c in columns]:
        return [], [(head_line, f"table columns must be exactly: {wanted}")]
    data = lines[1:]
    if data and is_alignment_row(split_row(data[0][1])):
        data = data[1:]
    rows, errors = [], []
    for number, line in data:
        cells = split_row(line)
        if len(cells) == len(columns):
            rows.append((number, cells))
        else:
            errors.append((number, f"row has {len(cells)} cells; expected {len(columns)}"))
    return rows, errors


def section_override(section_text, overrides, stage: str) -> bool:
    """True only for an `Override: O<n>` line naming an existing override that is open and is for `stage`."""
    m = OVERRIDE_LINE.search(section_text)
    found = overrides.get(m.group(1)) if m else None
    if found is None or found.status != "open":
        return False
    wanted = re.match(r"\s*([0-7])(?!\d)", str(stage))
    named = re.match(r"\s*([0-7])(?!\d)", found.stage)
    return bool(wanted and named and wanted.group(1) == named.group(1))


def _overridden(body, overrides, stage: str, file: str, heading: str):
    """(silenced, problems): an Override line that does not count is reported, and the section is still judged."""
    joined = "\n".join(line for _, line in body)
    m = OVERRIDE_LINE.search(joined)
    if m is None:
        return False, []
    if section_override(joined, overrides, stage):
        return True, []
    ident = m.group(1)
    line = next(n for n, text in body if text.startswith("Override:"))
    found = overrides.get(ident)
    if found is None:
        why = f"{ident} is not in {OVERRIDES_FILE}"
    elif found.status != "open":
        why = f"override {ident} is {found.status or 'not open'}; an override only counts while it is open"
    else:
        why = f"override {ident} is for stage '{found.stage}', not for stage {stage}"
    return False, [Problem(file, line, f"{heading}: {why}")]


def _clean_path(raw: str):
    """A file map path as git writes it, with a trailing slash kept for a folder; None for '/' or '.' alone."""
    path = raw.strip().strip("`").replace("\\", "/")
    if path.strip("/") in ("", "."):
        return None
    normal = posixpath.normpath(path)
    return normal + "/" if path.endswith("/") else normal


def file_map_problems(text, tracked, overrides, file: str = ARCHITECTURE_FILE) -> list[Problem]:
    """The file map must name every tracked file (a folder row covers what is below it) and nothing else."""
    section = _section(text, "File map")
    if section is None:
        return [Problem(file, 0, "no '## File map' section")]
    head, body = section
    silenced, problems = _overridden(body, overrides, "5", file, "File map")
    if silenced:
        return []
    rows, errors = _table(head, body, MAP_COLUMNS)
    problems += [Problem(file, n, m) for n, m in errors]
    tracked_set, covered = set(tracked), set()
    for number, (raw, description) in rows:
        path = _clean_path(raw)
        if path is None:
            problems.append(Problem(file, number, f"'{raw}' is refused: a row must name a file or a real folder, "
                                                  "not the whole project"))
            continue
        if not description.strip():
            problems.append(Problem(file, number, f"{path} has no description; say what it does"))
        if path.endswith("/"):
            inside = [t for t in tracked if t.startswith(path)]
            if not inside:
                problems.append(Problem(file, number, f"{path} matches no tracked file"))
                continue
            covered.update(inside)
            if len(inside) > MAX_FOLDER_FILES and not BULK.search(description):
                problems.append(Problem(file, number, f"{path} covers {len(inside)} files; a folder row may cover "
                                        f"at most {MAX_FOLDER_FILES} unless its description holds (bulk: <reason>)"))
        elif path in tracked_set:
            covered.add(path)
        else:
            problems.append(Problem(file, number, f"{path} is not a tracked file"))
    missing = [t for t in tracked if t not in covered]
    for name in missing[:20]:
        problems.append(Problem(file, head, f"{name} is tracked but not in the file map"))
    if len(missing) > 20:
        problems.append(Problem(file, head, f"and {len(missing) - 20} more tracked files are not in the file map"))
    return problems


def _dep_key(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().strip("`").lower())


def dependency_problems(text, deps, unreadable, overrides, file: str = ARCHITECTURE_FILE) -> list[Problem]:
    """The dependency table must list the direct dependencies of the manifests, with their pinned versions."""
    section = _section(text, "Dependencies")
    if section is None:
        return [Problem(file, 0, "no '## Dependencies' section")]
    head, body = section
    silenced, problems = _overridden(body, overrides, "5", file, "Dependencies")
    if silenced:
        return []
    manual = False
    for number, line in body:
        if line.startswith("Manifests:"):
            reason = re.fullmatch(r"Manifests:[ \t]*manual:[ \t]*(\S.*?)[ \t]*", line)
            if reason:
                manual = True
            else:
                problems.append(Problem(file, number, "write 'Manifests: manual: <reason>', with a reason"))
    rows, errors = _table(head, body, DEP_COLUMNS)
    problems += [Problem(file, n, m) for n, m in errors]
    listed = {}
    for number, cells in rows:
        for label, value in zip(DEP_COLUMNS, cells):
            if not value.strip():
                problems.append(Problem(file, number, f"{cells[0] or 'a row'}: '{label}' is blank"))
        listed[_dep_key(cells[0])] = (number, cells[0], cells[1])
    if manual:
        return problems                                        # taken as stated
    for path in unreadable:
        problems.append(Problem(file, head, f"{path} cannot be read by this check; list the dependencies by hand "
                                            "and add 'Manifests: manual: <reason>' to ## Dependencies"))
    manifest = {_dep_key(name): (name, version) for name, version in deps.items()}
    for key, (name, version) in sorted(manifest.items()):
        if key not in listed:
            problems.append(Problem(file, head, f"{name} is in a manifest but not in the dependency table"))
        elif version is not None and listed[key][2].strip() != version:
            problems.append(Problem(file, listed[key][0], f"{name}: the version in the table is "
                                    f"'{listed[key][2]}' but the manifest pins {version}"))
    for key, (number, name, _) in listed.items():
        if key not in manifest:
            problems.append(Problem(file, number, f"{name} is in the dependency table but in no manifest; "
                                                  "remove it or add 'Manifests: manual: <reason>'"))
    return problems


def _rung_problem(cell: str, root, tracked: set[str]):
    """Why a test-table cell is not acceptable evidence (None when it is)."""
    text = cell.strip()
    if not text:
        return "empty; name a tracked test or results file or a commit, or write 'n/a: <reason>'"
    if re.match(r"n/a\b", text, re.I):
        reason = re.fullmatch(r"n/a[ \t]*:[ \t]*(.*)", text, re.I | re.S)
        if reason and reason.group(1).strip() and not PLACEHOLDER.fullmatch(reason.group(1).strip()):
            return None
        return "'n/a' needs a reason: write 'n/a: <reason>'"
    for token in re.split(r"[\s,;()`'\"]+", text):
        token = token.split("::")[0].rstrip(".")
        if not token:
            continue
        if norm_path(token) in tracked:
            return None
        if re.fullmatch("[0-9a-f]{7,40}", token):
            resolved = resolve_commit(root, token)
            if resolved and is_ancestor(root, resolved, "HEAD"):
                return None
    return f"'{text}' holds no tracked file or commit on the current history; write one, or 'n/a: <reason>'"


def test_table_problems(text, size, parts, attack_rungs, tracked, root, overrides,
                        file: str = ARCHITECTURE_FILE) -> list[Problem]:
    """One row per part (a component, a REQ-n or an ATK-n); each required rung holds evidence or a reason."""
    section = _section(text, "Tests")
    if section is None:
        return [Problem(file, 0, "no '## Tests' section")]
    head, body = section
    silenced, problems = _overridden(body, overrides, "4", file, "Tests")
    if silenced:
        return []
    rows, errors = _table(head, body, TEST_COLUMNS)
    problems += [Problem(file, n, m) for n, m in errors]
    if not rows and not errors:
        problems.append(Problem(file, head, "the test table has no rows; every part needs one"))
    tracked_set, seen = set(tracked), {}
    rungs = (1, 2) if size == "small" else (1, 2, 3, 4, 5)
    for number, cells in rows:
        part = cells[0].strip("` ")
        if part not in parts:
            ids = REQ_ID.findall(part) + ATK_ID.findall(part)
            if len(ids) > 1:
                problems.append(Problem(file, number, f"'{part}' names more than one id; one part per row"))
            else:
                problems.append(Problem(file, number, f"'{part}' is not a part; the first cell must be exactly "
                                                      "one component, REQ-n or ATK-n"))
            continue
        if part in seen:
            problems.append(Problem(file, number, f"{part} has more than one row (first at line {seen[part]})"))
            continue
        seen[part] = number
        for rung in sorted(set(rungs) | ({attack_rungs[part]} if part in attack_rungs else set())):
            why = _rung_problem(cells[rung], root, tracked_set)
            if why:
                problems.append(Problem(file, number, f"{part}: rung {rung} ({TEST_COLUMNS[rung][2:]}): {why}"))
    for part in sorted(set(parts) - set(seen)):
        problems.append(Problem(file, head, f"{part} has no row in the test table"))
    return problems


def components(text) -> set[str]:
    section = _section(text, "Components")
    if section is None:
        return set()
    rows, _ = _table(section[0], section[1], COMPONENT_COLUMNS)
    return {cells[0].strip("` ") for _, cells in rows if cells[0].strip("` ")}


def requirement_ids(text) -> set[str]:
    return {m for line in clean_lines(text) for m in REQ_ID.findall(line)}


def _attack_rows(text: str):
    return _table(0, list(enumerate(clean_lines(text), start=1)), ATTACK_COLUMNS)


def attack_ids(text) -> set[str]:
    return {cells[0].strip("` ") for _, cells in _attack_rows(text)[0] if ATK_ID.fullmatch(cells[0].strip("` "))}


def attack_rungs(text) -> dict[str, int]:
    """Attack id to the rung (3 or 5) it must be tried at; attacks marked '-' are left out."""
    return {cells[0].strip("` "): int(cells[2]) for _, cells in _attack_rows(text)[0]
            if ATK_ID.fullmatch(cells[0].strip("` ")) and cells[2] in ("3", "5")}


def attack_problems(text, size, file: str = ATTACKS_FILE) -> list[Problem]:
    rows, errors = _attack_rows(text)
    problems = [Problem(file, n, m) for n, m in errors]
    for number, line in enumerate(clean_lines(text), start=1):
        if EXAMPLE_MARKER in line:
            problems.append(Problem(file, number, f"still contains the template marker {EXAMPLE_MARKER}; "
                                                  "replace the worked example"))
    needed = ATTACK_MINIMUM.get(size, ATTACK_MINIMUM["small"])
    if not errors and len(rows) < needed:
        problems.append(Problem(file, 0, f"{len(rows)} attack rows; a {size} project needs at least {needed}"))
    for position, (number, (ident, attack, rung, author)) in enumerate(rows, start=1):
        if ident.strip("` ") != f"ATK-{position}":
            problems.append(Problem(file, number, f"id '{ident}' should be ATK-{position}; ids run ATK-1, "
                                                  "ATK-2, ... in order"))
        if rung not in ("3", "5", "-"):
            problems.append(Problem(file, number, f"Rung '{rung}' must be 3, 5 or - (not needed)"))
        for label, value in (("Attack", attack), ("Drafted by", author)):
            if not value.strip():
                problems.append(Problem(file, number, f"'{label}' is blank"))
    return problems


# ------------------------------------------------------------------ manifests

def _requirements_deps(text: str):
    found = []
    for line in normalise(text).split("\n"):
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not line or line.startswith(("-", ".", "/")):
            continue
        if "://" in line and not re.match(r"[\w.-]+\s*(\[[^\]]*\])?\s*@", line):
            continue
        found.append(_pep508(line))
    return [f for f in found if f]


def _pep508(requirement: str):
    m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;]*)", requirement)
    if not m:
        return None
    pinned = re.search(r"(?<![=!<>~])==\s*([^\s,]+)", m.group(2))
    return _dep_key(m.group(1)), (pinned.group(1) if pinned and "*" not in pinned.group(1) else None)


def _pyproject_deps(text: str):
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    if "poetry" in (data.get("tool") or {}) or "dependency-groups" in data:
        return None
    project = data.get("project") or {}
    lists = [project.get("dependencies") or []]
    lists += list((project.get("optional-dependencies") or {}).values())
    found = [_pep508(item) for items in lists if isinstance(items, list) for item in items if isinstance(item, str)]
    return [f for f in found if f]


def _package_json_deps(text: str):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    found = []
    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            pinned = isinstance(version, str) and PINNED_NPM.fullmatch(version.strip())
            found.append((name, version.strip() if pinned else None))
    return found


def manifest_dependencies(root, tracked) -> tuple[dict[str, str | None], list[str]]:
    """(name to pinned version or None, manifest paths this check cannot read). Direct dependencies only."""
    root = Path(root)
    deps: dict[str, str | None] = {}
    unreadable: list[str] = []
    for rel in sorted(tracked):
        parts = rel.split("/")
        base = parts[-1]
        if "node_modules" in parts[:-1]:
            continue
        if base in UNREADABLE_MANIFESTS:
            unreadable.append(rel)
            continue
        if fnmatch.fnmatchcase(base.lower(), "requirements*.txt"):
            reader = _requirements_deps
        elif base == "pyproject.toml":
            reader = _pyproject_deps
        elif base == "package.json":
            reader = _package_json_deps
        else:
            continue
        path = root / rel
        text = decode(path.read_bytes(), rel)[0] if path.is_file() else None   # not UTF-8 counts as unreadable
        found = reader(text) if text is not None else None
        if found is None:
            unreadable.append(rel)
            continue
        for name, version in found:
            if deps.get(name) is None:
                deps[name] = version
    return deps, unreadable


def architecture_problems(root, tracked, stages, overrides) -> list[Problem]:
    """The checks that bind at a stage: attack list at 0, test table at 4, file map and dependencies at 5."""
    if stages is None or stages.size not in SIZES:
        return []

    def passed(n: int) -> bool:
        row = stages.rows.get(n)
        return row is not None and row.status == "passed"

    root, problems = Path(root), []
    attacks, found = _load(root, ATTACKS_FILE)
    if passed(0):
        problems += found
        if attacks is not None:
            problems += attack_problems(attacks, stages.size)
    if not (passed(4) or passed(5)):
        return problems
    text, found = _load(root, ARCHITECTURE_FILE)
    problems += found
    if text is None:
        if passed(5) and not found:
            problems.append(Problem(ARCHITECTURE_FILE, 0, "file is missing; copy templates/ARCHITECTURE.md into the "
                                                          "project and fill it in"))
        return problems
    if passed(4):
        requirements, _ = _load(root, REQUIREMENTS_FILE)
        parts = components(text) | requirement_ids(requirements or "") | attack_ids(attacks or "")
        problems += test_table_problems(text, stages.size, parts, attack_rungs(attacks or ""), tracked, root,
                                        overrides)
    if passed(5):
        problems += file_map_problems(text, tracked, overrides)
        deps, unreadable = manifest_dependencies(root, tracked)
        problems += dependency_problems(text, deps, unreadable, overrides)
    return problems


# ------------------------------------------------------ traits, size and go-live

class TraitRule(NamedTuple):
    """What shows a trait: file name patterns (matched on the lower-cased base name), folder names, dependencies."""
    files: tuple[str, ...] = ()
    folders: tuple[str, ...] = ()
    deps: tuple[str, ...] = ()


CONTAINER_FILES = ("dockerfile", "dockerfile.*", "*.dockerfile", "compose*.y*ml", "docker-compose*.y*ml")
LLM_DEPS = ("anthropic", "openai", "langchain", "litellm", "@anthropic-ai/sdk")
# Design section 9: the trait rules as data. `paid-api` also follows from every llm dependency.
TRAIT_RULES: dict[str, TraitRule] = {
    "container": TraitRule(files=CONTAINER_FILES),
    "database": TraitRule(files=("*.sql",), folders=("migrations",),
                          deps=("psycopg", "psycopg2-binary", "asyncpg", "sqlalchemy", "prisma", "pg", "mysql2")),
    "web": TraitRule(deps=("flask", "fastapi", "django", "streamlit", "express", "next")),
    "llm": TraitRule(deps=LLM_DEPS),
    "paid-api": TraitRule(deps=("stripe", "twilio", *LLM_DEPS)),
    "scheduled": TraitRule(files=("crontab",), deps=("celery", "apscheduler")),
}
SMALL_SOURCE_LIMIT = 10
SMALL_REFUSED_TRAITS = ("llm", "paid-api", "personal-data", "web")    # personal-data can only be declared
GO_LIVE_FILE = "GO-LIVE.md"
CHECKLIST_FILE = "checks/checklist.json"
GO_LIVE_COLUMNS = ["Risk", "Validation", "Source", "Status", "Evidence"]
GO_LIVE_STATUSES = ("proven", "not applicable", "overridden")


def _tracked_matching(tracked, patterns) -> list[str]:
    return [rel for rel in tracked
            if "node_modules" not in rel.split("/")[:-1]
            and any(fnmatch.fnmatchcase(rel.split("/")[-1].lower(), p) for p in patterns)]


def detect_traits(root, tracked, deps) -> set[str]:
    """Traits shown by the tracked files and the direct dependencies. `root` is part of the signature only."""
    names = {_dep_key(name) for name in deps}
    found = set()
    for trait, rule in TRAIT_RULES.items():
        in_folder = any(f in rel.lower().split("/")[:-1] and "node_modules" not in rel.split("/")[:-1]
                        for rel in tracked for f in rule.folders)
        if names & {_dep_key(d) for d in rule.deps} or _tracked_matching(tracked, rule.files) or in_folder:
            found.add(trait)
    return found


def size_problems(stages, tracked, traits, file: str = STAGES_FILE) -> list[Problem]:
    """`Size: small` is refused for a project that is too large for it, so Small cannot be used to escape."""
    if stages.size != "small":
        return []
    line = stages.size_line
    problems = [Problem(file, line, f"Size: small is refused: {rel} is tracked, and a container means the project "
                                    "is not small; use 'Size: full'")
                for rel in _tracked_matching(tracked, CONTAINER_FILES)]
    count = len([rel for rel in tracked if rel.lower().endswith(SOURCE_EXTENSIONS)])
    if count > SMALL_SOURCE_LIMIT:
        problems.append(Problem(file, line, f"Size: small is refused: {count} tracked source files; a small "
                                            f"project has at most {SMALL_SOURCE_LIMIT}; use 'Size: full'"))
    problems += [Problem(file, line, f"Size: small is refused: the project has the '{trait}' trait; "
                                     "use 'Size: full'")
                 for trait in sorted(set(traits) & set(SMALL_REFUSED_TRAITS))]
    return problems


def traits_line_problems(stages, unreadable, manual: bool, file: str = STAGES_FILE) -> list[Problem]:
    """With a manifest this check cannot read, traits cannot be detected, so the owner must state them."""
    if stages.traits is not None or not (unreadable or manual):
        return []
    why = ("a manifest this check cannot read (" + ", ".join(unreadable) + ")") if unreadable \
        else "dependencies listed by hand (Manifests: manual)"
    return [Problem(file, 0, f"no 'Traits:' line, but the project has {why}, so traits cannot be detected; write "
                             "'Traits: none' or list them (for example 'Traits: web, personal-data')")]


def required_go_live_ids(traits, checklist: list[dict], attacks: set[str]) -> set[str]:
    """Every attack id, and every checklist item that applies always or to one of the traits."""
    required = set(attacks)
    for item in checklist:
        applies = set(item.get("applies_when") or ())
        if "always" in applies or applies & set(traits):
            required.add(item["id"])
    return required


def load_checklist(root):
    """(items, problems) from checks/checklist.json: a list of {"id": str, "applies_when": [str]}."""
    path = Path(root) / CHECKLIST_FILE
    if not path.is_file():
        return [], [Problem(CHECKLIST_FILE, 0, "file is missing; the go-live review needs the checklist "
                                                "(copy it into the project)")]
    text, problem = decode(path.read_bytes(), CHECKLIST_FILE)
    if problem:
        return [], [problem]
    try:
        data = json.loads(normalise(text))
    except (ValueError, RecursionError) as error:
        return [], [Problem(CHECKLIST_FILE, getattr(error, "lineno", 0) or 0, f"not valid JSON: {error}")]
    if not isinstance(data, list):
        return [], [Problem(CHECKLIST_FILE, 0, "must be a JSON list of items {\"id\": ..., \"applies_when\": [...]}")]
    items, problems, seen = [], [], set()
    for position, item in enumerate(data, start=1):
        ident = item.get("id") if isinstance(item, dict) else None
        applies = item.get("applies_when") if isinstance(item, dict) else None
        if not (isinstance(ident, str) and ident.strip()):
            problems.append(Problem(CHECKLIST_FILE, 0, f"item {position} has no text 'id'"))
        elif not (isinstance(applies, list) and all(isinstance(a, str) for a in applies)):
            problems.append(Problem(CHECKLIST_FILE, 0, f"item {ident} needs 'applies_when' as a list of text"))
        elif ident in seen:
            problems.append(Problem(CHECKLIST_FILE, 0, f"item id {ident} appears twice"))
        else:
            seen.add(ident)
            items.append({"id": ident, "applies_when": [a.strip().lower() for a in applies]})
    return items, problems


def manual_manifests(architecture_text: str) -> bool:
    """True when ARCHITECTURE.md carries 'Manifests: manual: <reason>' in its Dependencies section."""
    section = _section(architecture_text, "Dependencies")
    return bool(section) and any(re.fullmatch(r"Manifests:[ \t]*manual:[ \t]*\S.*", line) for _, line in section[1])


def _blank(value: str) -> bool:
    return not value.strip() or bool(PLACEHOLDER.fullmatch(value.strip()))


def go_live_problems(text, required: set[str], overrides, file: str = GO_LIVE_FILE) -> list[Problem]:
    """One resolved row for each required id; a Source cell holds exactly one id or free text."""
    rows, errors = _table(0, list(enumerate(clean_lines(text), start=1)), GO_LIVE_COLUMNS)
    problems = [Problem(file, n, m) for n, m in errors]
    if not rows and not errors:
        problems.append(Problem(file, 0, "no rows; every required id needs a row"))
    first_row: dict[str, int] = {}
    for number, cells in rows:
        risk, validation, source, status, evidence = cells
        label = source.strip("` ") or "a row"
        if any(EXAMPLE_MARKER in cell for cell in cells):
            problems.append(Problem(file, number, f"still contains the template marker {EXAMPLE_MARKER}; "
                                                  "replace the worked example"))
        for name, value in (("Risk", risk), ("Validation", validation), ("Source", source)):
            if not value.strip():
                problems.append(Problem(file, number, f"{label}: '{name}' is blank"))
        named = sorted({t.strip("`.") for t in re.split(r"[\s,;]+", source)
                        if t.strip("`.") in required or ATK_ID.fullmatch(t.strip("`."))})
        if len(named) > 1:
            problems.append(Problem(file, number, f"'{source}' names more than one id ({', '.join(named)}); "
                                                  "one id per row"))
        if label in required:
            if label in first_row:
                problems.append(Problem(file, number, f"{label} has more than one row (first at line "
                                                      f"{first_row[label]})"))
            else:
                first_row[label] = number
        problems += _go_live_status_problems(number, label, status, evidence, overrides, file)
    problems += [Problem(file, 0, f"{ident} has no row; add one whose Source is exactly {ident}")
                 for ident in sorted(required - set(first_row))]
    return problems


def _go_live_status_problems(number, label, status, evidence, overrides, file) -> list[Problem]:
    state = status.strip().casefold()
    if state == "proven":
        if _blank(evidence):
            return [Problem(file, number, f"{label}: proven but has no evidence; write the command and its result")]
    elif state == "not applicable":
        if _blank(evidence):
            return [Problem(file, number, f"{label}: not applicable but gives no reason; write the reason")]
    elif state == "overridden":
        ident = evidence.strip()
        if not re.fullmatch(r"O\d+", ident):
            return [Problem(file, number, f"{label}: overridden, but Evidence does not name an override "
                                          "(for example O1)")]
        return _overridden([(number, f"Override: {ident}")], overrides, "5", file, label)[1]
    else:
        return [Problem(file, number, f"{label}: unresolved (status '{status}'); it must be one of: "
                                      + ", ".join(GO_LIVE_STATUSES))]
    return []


# ----------------------------------------------------------------- OWNERSHIP.md

OWNERSHIP_FILE = "OWNERSHIP.md"
TOPICS = ("what-it-does", "how-it-breaks", "how-to-recover")
EXPLAIN_COLUMNS = ["Topic", "Question", "Answer", "Gap", "Status"]
ROUND_COLUMNS = ["Question", "Answer", "Gap", "Status"]
OWNERSHIP_LINES = ("Hand-changed commit", "Closed", "Re-check due", "Re-check done", "Graded by")
OWNERSHIP_LINE = re.compile(r"^(" + "|".join(OWNERSHIP_LINES) + r"):[ \t]*(.*?)[ \t]*$")
MIN_ROUND = 3
RECHECK_DAYS = 7


def _ownership_lines(text: str) -> dict[str, tuple[str, int]]:
    """{label: (value, line)} for the first of each labelled line outside comments and code fences."""
    found: dict[str, tuple[str, int]] = {}
    for number, line in enumerate(clean_lines(text), start=1):
        m = OWNERSHIP_LINE.match(line)
        if m and m.group(1) not in found:
            found[m.group(1)] = (m.group(2), number)
    return found


def _answer_rows_problems(rows, question_at, answer_at, gap_at, status_at, label_of, file):
    """(answered count, problems) for the rows of an explain-back or full-round table."""
    answered, problems = 0, []
    for number, cells in rows:
        label = label_of(cells)
        if any(EXAMPLE_MARKER in cell for cell in cells):
            problems.append(Problem(file, number, f"{label}: still contains the template marker {EXAMPLE_MARKER}; "
                                                  "replace the worked example"))
        if not cells[question_at].strip():
            problems.append(Problem(file, number, f"{label}: Question is blank"))
        if _blank(cells[answer_at]):
            problems.append(Problem(file, number, f"{label}: the answer is blank; the owner's words go here"))
        else:
            answered += 1
        if not cells[gap_at].strip():
            problems.append(Problem(file, number, f"{label}: Gap is blank; the grading session writes the gap, "
                                                  "or '-' when there is none"))
        state = cells[status_at].strip().casefold()
        if state not in ("open", "closed"):
            problems.append(Problem(file, number, f"{label}: Status '{cells[status_at]}' must be open or closed"))
        elif state == "open":
            problems.append(Problem(file, number, f"{label}: the gap is still open ({cells[gap_at].strip() or '-'}); "
                                                  "close it or log an override"))
    return answered, problems


def explain_back_problems(text, overrides, file: str = OWNERSHIP_FILE) -> list[Problem]:
    """Stage 5: one answered, closed row for each of the three topics."""
    section = _section(text, "Explain-back")
    if section is None:
        return [Problem(file, 0, "no '## Explain-back' section")]
    head, body = section
    silenced, problems = _overridden(body, overrides, "5", file, "Explain-back")
    if silenced:
        return []
    rows, errors = _table(head, body, EXPLAIN_COLUMNS)
    problems += [Problem(file, n, m) for n, m in errors]
    _, found = _answer_rows_problems(rows, 1, 2, 3, 4, lambda cells: cells[0].strip("` ") or "a row", file)
    problems += found
    topics = {cells[0].strip("` ") for _, cells in rows}
    problems += [Problem(file, number, f"'{cells[0]}' is not a topic; use one of: {', '.join(TOPICS)}")
                 for number, cells in rows if cells[0].strip("` ") not in TOPICS]
    if not errors:
        problems += [Problem(file, head, f"no row for the topic {topic}") for topic in TOPICS if topic not in topics]
    return problems


def ownership_problems(text, root, tracked, size, components: int, overrides,
                       file: str = OWNERSHIP_FILE) -> list[Problem]:
    """Stage 6: the full round, the hand-changed commit, the grader and the re-check dates.

    `tracked` is part of the signature only; the hand-changed commit is judged from history."""
    problems = _full_round_problems(text, size, components, overrides, file)
    lines = _ownership_lines(text)
    for label in OWNERSHIP_LINES:
        if label not in lines:
            problems.append(Problem(file, 0, f"missing the line '{label}: ...'"))
    if "Hand-changed commit" in lines:
        value, number = lines["Hand-changed commit"]
        problems += _hand_change_problems(Path(root), value, number, file)
    if "Graded by" in lines and _blank(lines["Graded by"][0]):
        problems.append(Problem(file, lines["Graded by"][1], "Graded by is empty; name the separate session that "
                                                             "compared the answers with the code"))
    problems += _recheck_date_problems(lines, file)
    return problems


def _full_round_problems(text, size, components: int, overrides, file) -> list[Problem]:
    section = _section(text, "Full round")
    if section is None:
        return [Problem(file, 0, "no '## Full round' section")]
    head, body = section
    silenced, problems = _overridden(body, overrides, "6", file, "Full round")
    if silenced:
        return []
    rows, errors = _table(head, body, ROUND_COLUMNS)
    problems += [Problem(file, n, m) for n, m in errors]
    answered, found = _answer_rows_problems(rows, 0, 1, 2, 3, lambda cells: cells[0].strip() or "a row", file)
    problems += found
    needed = max(MIN_ROUND, components) if size == "full" else MIN_ROUND
    if not errors and answered < needed:
        problems.append(Problem(file, head, f"{answered} answered questions; a {size or 'small'} project needs at "
                                            f"least {needed}"))
    return problems


def _hand_change_problems(root: Path, value: str, number: int, file: str) -> list[Problem]:
    if not re.fullmatch("[0-9a-f]{7,40}", value):
        return [Problem(file, number, f"Hand-changed commit '{value}' is not a hexadecimal hash (7 to 40 "
                                      "characters from 0-9 and a-f)")]
    resolved = resolve_commit(root, value)
    if not (resolved and is_ancestor(root, resolved, "HEAD")):
        return [Problem(file, number, f"Hand-changed commit {value} is not in the history of the current branch")]
    changed = (git_text(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", resolved) or "")
    if not any(name.lower().endswith(SOURCE_EXTENSIONS) for name in changed.split("\n")):
        return [Problem(file, number, f"Hand-changed commit {value} touches no source file; it must be the "
                                      "commit where the owner changed code by hand")]
    return []


def _recheck_date_problems(lines, file) -> list[Problem]:
    problems = []
    for label in ("Closed", "Re-check due"):
        if label in lines and not _is_date(lines[label][0]):
            problems.append(Problem(file, lines[label][1], f"{label} '{lines[label][0]}' must be a date like "
                                                           "2026-11-09"))
    if "Re-check done" in lines and lines["Re-check done"][0] != "-" and not _is_date(lines["Re-check done"][0]):
        problems.append(Problem(file, lines["Re-check done"][1], f"Re-check done '{lines['Re-check done'][0]}' must "
                                                                  "be '-' or a date like 2026-11-09"))
    if all(label in lines and _is_date(lines[label][0]) for label in ("Closed", "Re-check due")):
        closed = date.fromisoformat(lines["Closed"][0])
        if date.fromisoformat(lines["Re-check due"][0]) != closed + timedelta(days=RECHECK_DAYS):
            problems.append(Problem(file, lines["Re-check due"][1], f"Re-check due must be exactly {RECHECK_DAYS} "
                                    f"days after Closed ({closed + timedelta(days=RECHECK_DAYS)})"))
    return problems


def recheck_note(text, today: date) -> str | None:
    """A reminder (never a failure) when the re-check date has come and the re-check is not recorded as done."""
    lines = _ownership_lines(text)
    due, done = lines.get("Re-check due"), lines.get("Re-check done")
    if due is None or not _is_date(due[0]) or (done is not None and _is_date(done[0])):
        return None
    if today < date.fromisoformat(due[0]):
        return None
    return (f"re-check was due {due[0]} and is not recorded as done: ask the owner the {OWNERSHIP_FILE} questions "
            "again before other work, then fill in 'Re-check done'")


# ---------------------------------------------------------------- stage wiring

def _project_traits(root: Path, tracked, stages):
    """(traits, unreadable manifests): detected traits plus the traits declared in STAGES.md."""
    deps, unreadable = manifest_dependencies(root, tracked)
    return detect_traits(root, tracked, deps) | (stages.traits or set()), unreadable


def go_live_ownership_problems(root, tracked, stages, overrides, today: date):
    """(problems, notes): the size rule always; go-live and explain-back at 5 passed; the full round at 6 passed."""
    if stages is None:
        return [], []
    root = Path(root)
    traits, unreadable = _project_traits(root, tracked, stages)
    problems = size_problems(stages, tracked, traits)
    notes: list[str] = []

    def passed(n: int) -> bool:
        return n in stages.rows and stages.rows[n].status == "passed"

    architecture, _ = _load(root, ARCHITECTURE_FILE)
    ownership, found = _load(root, OWNERSHIP_FILE)
    if passed(5):
        problems += traits_line_problems(stages, unreadable, manual_manifests(architecture or ""))
        problems += _go_live_stage_problems(root, tracked, stages, overrides, traits)
        if ownership is not None:
            problems += explain_back_problems(ownership, overrides)
    if passed(6) and ownership is not None:
        problems += ownership_problems(ownership, root, tracked, stages.size, len(components(architecture or "")),
                                       overrides)
        note = recheck_note(ownership, today)
        if note:
            notes.append(note)
    return problems + (found if passed(5) or passed(6) else []), notes


def _go_live_stage_problems(root, tracked, stages, overrides, traits) -> list[Problem]:
    checklist, problems = load_checklist(root)
    attacks, _ = _load(root, ATTACKS_FILE)
    required = required_go_live_ids(traits, checklist, attack_ids(attacks or ""))
    if not required:
        return problems
    row = stages.rows[5]
    named = [norm_path(v) for k, v in parse_evidence(row.evidence)[0] if k == "file"]
    if GO_LIVE_FILE not in named:
        problems.append(Problem(STAGES_FILE, row.line, f"{row.name}: the evidence must include "
                                                       f"'file:{GO_LIVE_FILE}'"))
    text, found = _load(root, GO_LIVE_FILE)
    problems += found
    if text is not None:
        problems += go_live_problems(text, required, overrides)
    return problems


def go_live_report(root: Path) -> tuple[list[str], list[str]]:
    """(stdout lines, stderr lines) of `--go-live`: the traits and the ids GO-LIVE.md must cover."""
    require_checkable_repo(root)
    tracked = tracked_files(root)
    stages_text, _ = _load(root, STAGES_FILE)
    stages = parse_stages(stages_text or "")
    traits, _ = _project_traits(root, tracked, stages)
    checklist, found = load_checklist(root)
    attacks, _ = _load(root, ATTACKS_FILE)
    required = required_go_live_ids(traits, checklist, attack_ids(attacks or ""))
    natural = lambda ident: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ident)]   # noqa: E731
    out = ["traits: " + (", ".join(sorted(traits)) or "none"), f"required ids ({len(required)}):"]
    out += [f"  {ident}" for ident in sorted(required, key=natural)]
    err = [f"{p.file}: {p.message}; only the attack ids are listed" for p in found]
    return out, err


# --------------------------------------------------------------------- command

def _load(root: Path, name: str):
    """(text, problems): text is None when the file is absent or not UTF-8."""
    path = root / name
    if not path.is_file():
        return None, []
    text, problem = decode(path.read_bytes(), name)
    return text, [problem] if problem else []


def check_project(root, today: date | None = None) -> tuple[list[Problem], list[str]]:
    """(problems, notes) for a project folder. `today` (default: the current date) only decides the re-check note."""
    root = Path(root)
    require_checkable_repo(root)
    tracked = tracked_files(root)
    problems: list[Problem] = []
    notes: list[str] = []
    stages_text, found = _load(root, STAGES_FILE)
    problems += found
    stages = None
    if stages_text is not None:
        stages = parse_stages(stages_text)
    elif not found:
        problems.append(Problem(STAGES_FILE, 0, "file is missing; copy templates/STAGES.md into the project"))
    overrides_text, found = _load(root, OVERRIDES_FILE)
    problems += found
    overrides = parse_overrides(overrides_text or "")
    if stages_text is not None:
        problems += stage_problems(stages_text, root, tracked, overrides, STAGES_FILE)
    if overrides_text is not None or not found:
        problems += override_problems(overrides_text, root, stages, OVERRIDES_FILE)
    problems += architecture_problems(root, tracked, stages, overrides)
    found, more = go_live_ownership_problems(root, tracked, stages, overrides, today or date.today())
    problems += found
    notes += more
    notes += [f"open override {ident} (stage {o.stage}): see {OVERRIDES_FILE}"
              for ident, o in overrides.items() if o.status == "open"]
    problems = sorted(set(problems), key=lambda p: (p.file, p.line, p.message))   # one report per problem
    return problems, notes


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    print(TRUST_LIMIT, file=sys.stderr)
    go_live = "--go-live" in args
    args = [a for a in args if a != "--go-live"]
    if len(args) > 1:
        print("usage: check_gates.py [--go-live] [project folder]", file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path.cwd()
    if not root.is_dir():
        print(f"check_gates.py: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        if go_live:
            out, err = go_live_report(root)
            print("\n".join(out))
            for line in err:
                print(f"note: {line}", file=sys.stderr)
            return 0
        problems, notes = check_project(root)
    except GateError as error:
        print(f"check_gates.py: {error}", file=sys.stderr)
        return 2
    for p in problems:
        print(f"{p.file}:{p.line}: {p.message}")
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
