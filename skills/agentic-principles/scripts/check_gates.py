"""Stage gate: checks that each stage marked done in STAGES.md has the evidence its gate needs.

Usage: python check_gates.py [project folder]   (default: the current directory)
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
  command           check_project and main
"""
from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
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
    if any(re.search(r"\bREQ-\d+\b", line) for line in clean_lines(text)):
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
# STUBS: signatures only, so that each test class fails on its own assertions. Replaced by the real code.

def manifest_dependencies(root, tracked) -> tuple[dict, list]:
    return {}, []


def file_map_problems(text, tracked, overrides, file="ARCHITECTURE.md") -> list[Problem]:
    return []


def dependency_problems(text, deps, unreadable, overrides, file="ARCHITECTURE.md") -> list[Problem]:
    return []


def test_table_problems(text, size, parts, attack_rungs, tracked, root, overrides,
                        file="ARCHITECTURE.md") -> list[Problem]:
    return []


def attack_problems(text, size, file="ATTACKS.md") -> list[Problem]:
    return []


def requirement_ids(text) -> set:
    return set()


def attack_rungs(text) -> dict:
    return {}


def components(text) -> set:
    return set()


def section_override(section_text, overrides, stage) -> bool:
    return False


# --------------------------------------------------------------------- command

def _load(root: Path, name: str):
    """(text, problems): text is None when the file is absent or not UTF-8."""
    path = root / name
    if not path.is_file():
        return None, []
    text, problem = decode(path.read_bytes(), name)
    return text, [problem] if problem else []


def check_project(root, today: date | None = None) -> tuple[list[Problem], list[str]]:
    """(problems, notes) for a project folder. `today` is reserved for the date-based checks of later versions."""
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
    notes += [f"open override {ident} (stage {o.stage}): see {OVERRIDES_FILE}"
              for ident, o in overrides.items() if o.status == "open"]
    problems.sort(key=lambda p: (p.file, p.line))
    return problems, notes


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    print(TRUST_LIMIT, file=sys.stderr)
    if len(args) > 1:
        print("usage: check_gates.py [project folder]", file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path.cwd()
    if not root.is_dir():
        print(f"check_gates.py: not a directory: {root}", file=sys.stderr)
        return 2
    try:
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
