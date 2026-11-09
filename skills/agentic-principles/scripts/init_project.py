"""Project setup: starts or adopts a project under the agentic-principles skill.

Usage:
  init_project.py <folder> --size small|full --method normal|sub-agent [--adopt-at N]
  init_project.py --update-checks <folder>     replace the copied check scripts, keeping a .bak of each changed one
  init_project.py --new-cycle <folder>         archive STAGES.md under docs/archive/ and start a fresh one
  init_project.py --where                      print the folder that holds principles/ and checklist/
Exit codes: 0 done, 2 a bad value, a missing folder, or a file that cannot be handled safely.

What init does: copies the templates and the check scripts into the project (OWNERSHIP.md with its Record line
naming the companion repo ../<project>-internal, and the private record template into that repo when it exists),
writes a marked block into its CLAUDE.md and adds a continuous-integration workflow. Every copied file is opened in create-only mode, so a
file that already exists is never overwritten and is reported as kept. The only exceptions are the marked
CLAUDE.md block, --update-checks (which keeps a backup) and --new-cycle (which archives first).
It does not commit and does not run git: the owner commits what it created.

Layout (one file, standard library only):
  data        the file lists and the CLAUDE.md block text
  helpers     folder and file handling that never overwrites
  commands    init, claude_block, update_checks, new_cycle, where
  command     argument parsing and main
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import check_gates
except ImportError:                                   # imported from another folder: look next to this file
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_gates

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "templates"
STAGES_FILE = "STAGES.md"
COMMON = ("DECISIONS.md", "AI-Agents.md", "REQUIREMENTS.md", "ATTACKS.md", "GLOSSARY.md", "BUILD-LEDGER.md",
          STAGES_FILE, "ARCHITECTURE.md", "OWNERSHIP.md", "GRILLING.md")
FULL_ONLY = ("OVERRIDES.md", "GO-LIVE.md")
OWNERSHIP_FILE = "OWNERSHIP.md"
RECORD_TEMPLATE = "OWNERSHIP-RECORD.md"
RECORD_LINE = "Record: ../<project>-internal/ownership/OWNERSHIP.md"
COMPANION_SUFFIX = "-internal"
WORKFLOW = ".github/workflows/agentic-checks.yml"
ARCHIVE_DIR = "docs/archive"
# Where each copied check lives in the project, and where it comes from in this repository.
CHECKS = {
    "checks/check_docs.py": REPO / "checks" / "check_docs.py",
    "checks/check_gates.py": Path(check_gates.__file__).resolve(),
    "checks/checklist.json": REPO / "checklist" / "checklist.json",
}
BLOCK_OPEN = "<!-- agentic-principles -->"
BLOCK_CLOSE = "<!-- /agentic-principles -->"
BLOCK_BODY = (
    "## Agentic principles\n"
    "\n"
    "This project runs under the agentic-principles skill. Load that skill at the start of every session, "
    "before any other work.\n"
    "The current stage is recorded in STAGES.md. Work on that stage and do not skip ahead.\n"
    "A companion skill may end by naming its own \"next step\". The current stage in STAGES.md comes first; "
    "go back to it.\n"
    "If two skills differ on who does what, the overlap table in the agentic-principles skill wins.")
BLOCK = f"{BLOCK_OPEN}\n{BLOCK_BODY}\n{BLOCK_CLOSE}"


class InitError(Exception):
    """A bad argument or an unusable folder or file; the command exits with code 2."""


@dataclass
class Report:
    created: list[str] = field(default_factory=list)    # files written for the first time
    kept: list[str] = field(default_factory=list)       # files that already existed and were left as they are
    updated: list[str] = field(default_factory=list)    # files replaced (update_checks, new_cycle)
    backups: list[str] = field(default_factory=list)    # backup copies made before a replacement
    notes: list[str] = field(default_factory=list)      # what the owner should do next


# --------------------------------------------------------------------- helpers

def _folder(target) -> Path:
    root = Path(target)
    if not root.is_dir():
        raise InitError(f"not a folder: {root}")
    return root


def _source_bytes(path: Path) -> bytes:
    if not path.is_file():
        raise InitError(f"{path} is missing; this script must run from a complete copy of the repository")
    return path.read_bytes()


def _safe(root: Path, rel: str) -> Path:
    """root/rel, refused when the file or any folder on the way to it is a link, or when it resolves outside root.

    A link inside a cloned project could otherwise lead a write to a file outside the project."""
    isjunction = getattr(os.path, "isjunction", lambda _path: False)
    probe = root
    for part in Path(rel).parts:
        probe = probe / part
        if probe.is_symlink() or isjunction(probe):
            raise InitError(f"{rel} is or passes through a link ({probe}); a link could lead the write outside "
                            "the project, so nothing was written. Replace the link with a real file or folder")
    path = root / rel
    try:
        inside = path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        inside = False
    if not inside:
        raise InitError(f"{rel} resolves to a place outside the project folder; nothing was written")
    return path


def _replace(path: Path, data: bytes) -> None:
    """Replace an existing file: write a temporary file in the same folder, then swap it in."""
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        with open(tmp, "xb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except OSError as error:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise InitError(f"cannot replace {path}: {error}") from error


def _write_new(path: Path, data: bytes) -> bool:
    """Create the file with `data`; False (and nothing changed) when it already exists. Never overwrites."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "xb") as handle:
            handle.write(data)
    except FileExistsError:
        return False
    except OSError as error:
        raise InitError(f"cannot create {path}: {error}") from error
    return True


def _decode(data: bytes, name: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InitError(f"{name} is not valid UTF-8 (byte {error.start}); save it as UTF-8 first") from error


def _check_values(size, method, adopt_at) -> None:
    if size not in check_gates.SIZES:
        raise InitError(f"size must be one of: {', '.join(check_gates.SIZES)} (got '{size}')")
    if method not in check_gates.METHODS:
        raise InitError(f"method must be one of: {', '.join(check_gates.METHODS)} (got '{method}')")
    if adopt_at is not None:
        if isinstance(adopt_at, bool) or not isinstance(adopt_at, int) or not 1 <= adopt_at <= check_gates.MAX_ADOPTED_AT:
            raise InitError(f"adopt-at must be a stage number from 1 to {check_gates.MAX_ADOPTED_AT} "
                            f"(got '{adopt_at}'); stages 5 Ship and 6 Own are always done under the process")


def _replace_line(lines: list[str], old: str, new: list[str]) -> list[str]:
    """Replace the one line equal to `old`; the template layout changing is an error, never a silent skip."""
    hits = [i for i, line in enumerate(lines) if line == old]
    if len(hits) != 1:
        raise InitError(f"templates/{STAGES_FILE} no longer has exactly one line '{old}' ({len(hits)} found)")
    return lines[:hits[0]] + new + lines[hits[0] + 1:]


def render_stages(size: str, method: str, adopt_at: int | None = None, traits: set[str] | None = None,
                  cycle: int = 1) -> bytes:
    """The STAGES.md template with Size, Method, Cycle and optional Adopted-at, Traits and adopted rows filled in."""
    text = _decode(_source_bytes(TEMPLATES / STAGES_FILE), STAGES_FILE).lstrip("﻿").replace("\r\n", "\n")
    lines = text.split("\n")
    lines = _replace_line(lines, "Size: small", [f"Size: {size}"])
    extra = [f"Adopted-at: {adopt_at}"] if adopt_at is not None else []
    if traits is not None:
        extra.append("Traits: " + (", ".join(sorted(traits)) or "none"))
    lines = _replace_line(lines, "Method: normal", [f"Method: {method}"])
    lines = _replace_line(lines, "Cycle: 1", [f"Cycle: {cycle}", *extra])
    for n in range(adopt_at or 0):
        name = check_gates.STAGE_NAMES[n]
        lines = _replace_line(lines, f"| {name} | open | - | - |", [f"| {name} | adopted | - | - |"])
    return "\n".join(lines).encode("utf-8")


def render_ownership(project: str) -> bytes:
    """The OWNERSHIP.md template with the Record line naming this project's companion repo."""
    text = _decode(_source_bytes(TEMPLATES / OWNERSHIP_FILE), OWNERSHIP_FILE)
    if text.count(RECORD_LINE) != 1:
        raise InitError(f"templates/{OWNERSHIP_FILE} no longer has exactly one line '{RECORD_LINE}'")
    return text.replace(RECORD_LINE, RECORD_LINE.replace("<project>", project)).encode("utf-8")


def _companion_record(root: Path, report: Report) -> None:
    """Create the private record from its template in the companion repo next to the project, when that repo exists.
    Never overwrites; with no companion, writes nothing outside the project and says how to make one."""
    name = root.resolve().name
    companion = root.resolve().parent / f"{name}{COMPANION_SUFFIX}"
    rel = f"../{name}{COMPANION_SUFFIX}/ownership/{OWNERSHIP_FILE}"
    if not companion.is_dir():
        report.notes.append(f"No private companion repo {name}{COMPANION_SUFFIX} next to the project: the owner's "
                            "ownership answers have nowhere to go, and check_gates.py fails at stage 5 until "
                            f"{rel} can be read. Make it with repo-kickoff: scaffold_project.py <project folder> "
                            f"--id {name} --co-author claude|none --internal-only, then run init again")
        return
    if any(p.is_symlink() for p in (companion, companion / "ownership")):
        raise InitError(f"{companion} or its ownership folder is a link; nothing was written there")
    data = _source_bytes(TEMPLATES / RECORD_TEMPLATE)
    (report.created if _write_new(companion / "ownership" / OWNERSHIP_FILE, data) else report.kept).append(rel)
    report.notes.append(f"{rel} is in the companion repo: commit it there, never in this project")


def _claude_path(root: Path) -> Path:
    """CLAUDE.md at the top, or .claude/CLAUDE.md when that is the layout the project uses."""
    top, nested = root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"
    return nested if nested.is_file() and not top.is_file() else top


# -------------------------------------------------------------------- commands

def claude_block(existing: str) -> str:
    """`existing` CLAUDE.md text with the marked block added once, or refreshed when it is already there."""
    eol = "\r\n" if "\r\n" in existing else "\n"
    text = existing.replace("\r\n", "\n")
    opens, closes = text.count(BLOCK_OPEN), text.count(BLOCK_CLOSE)
    if opens != closes or opens > 1 or (opens == 1 and text.index(BLOCK_CLOSE) < text.index(BLOCK_OPEN)):
        raise InitError(f"CLAUDE.md has {opens} '{BLOCK_OPEN}' and {closes} '{BLOCK_CLOSE}' markers; there must be "
                        "one of each, opening first. Fix the markers by hand, then run again")
    if opens == 1:
        start, end = text.index(BLOCK_OPEN), text.index(BLOCK_CLOSE) + len(BLOCK_CLOSE)
        result = text[:start] + BLOCK + text[end:]
    elif not text.strip():
        result = BLOCK + "\n"
    else:
        result = text.rstrip("\n") + "\n\n" + BLOCK + "\n"
    return result.replace("\n", eol)


def init(target, size, method, adopt_at=None) -> Report:
    """Copy the process into `target`. Nothing is written until every value and every source has been checked."""
    root = _folder(target)
    _check_values(size, method, adopt_at)
    files: list[tuple[str, bytes]] = []
    for name in COMMON + (FULL_ONLY if size == "full" else ()):
        if name == STAGES_FILE:
            data = render_stages(size, method, adopt_at)
        elif name == OWNERSHIP_FILE:
            data = render_ownership(root.resolve().name)
        else:
            data = _source_bytes(TEMPLATES / name)
        files.append((name, data))
    files += [(rel, _source_bytes(source)) for rel, source in CHECKS.items()]
    files.append((WORKFLOW, _source_bytes(TEMPLATES / "agentic-checks.yml")))
    claude = _claude_path(root)
    claude_rel = claude.relative_to(root).as_posix()
    targets = [(rel, _safe(root, rel), data) for rel, data in files]
    _safe(root, claude_rel)
    before = claude.read_bytes() if claude.is_file() else None
    after = claude_block(_decode(before, claude.name) if before is not None else "").encode("utf-8")
    report = Report()
    for rel, path, data in targets:
        (report.created if _write_new(path, data) else report.kept).append(rel)
    if before != after:
        if before is None:
            _write_new(claude, after)
        else:
            _replace(claude, after)
        report.created.append(claude_rel)
    _companion_record(root, report)
    report.notes.append("Nothing was committed. Read what was created, then commit it; the first commit of "
                        f"{STAGES_FILE} is the start the gate measures from.")
    return report


def update_checks(target) -> Report:
    """Bring the copied check scripts and the checklist up to date; a changed file is backed up first."""
    root = _folder(target)
    wanted = {rel: _source_bytes(source) for rel, source in CHECKS.items()}
    paths = {rel: _safe(root, rel) for rel in wanted}
    report = Report()
    for rel, data in wanted.items():
        path = paths[rel]
        if _write_new(path, data):
            report.created.append(rel)
            continue
        old = path.read_bytes()
        if old == data:
            report.kept.append(rel)
            continue
        number, backup = 1, f"{rel}.bak"
        while not _write_new(_safe(root, backup), old):         # an earlier backup is never overwritten
            number += 1
            backup = f"{rel}.bak{number}"
        _replace(path, data)
        report.updated.append(rel)
        report.backups.append(backup)
    return report


def new_cycle(target) -> Report:
    """Archive STAGES.md as docs/archive/STAGES-cycle-N.md and write a fresh one with the same Size and Method."""
    root = _folder(target)
    path = _safe(root, STAGES_FILE)
    _safe(root, ARCHIVE_DIR)
    if not path.is_file():
        raise InitError(f"{path} does not exist; there is no cycle to archive")
    old = path.read_bytes()
    stages = check_gates.parse_stages(_decode(old, STAGES_FILE))
    if stages.size is None or stages.method is None:
        raise InitError(f"{STAGES_FILE} has no readable Size and Method lines; fix them first, so the new cycle "
                        "can keep them")
    cycle = (stages.cycle or 1) + 1
    fresh = render_stages(stages.size, stages.method, None, stages.traits, cycle)
    number = 1
    while not _write_new(_safe(root, f"{ARCHIVE_DIR}/STAGES-cycle-{number}.md"), old):
        number += 1
    archive = f"{ARCHIVE_DIR}/STAGES-cycle-{number}.md"
    _replace(path, fresh)
    report = Report(created=[archive], updated=[STAGES_FILE])
    report.notes.append(
        f"{STAGES_FILE} now says Cycle: {cycle}. Commit it together with {archive}, or in two commits; either way "
        "the gate measures commit evidence from the oldest commit whose STAGES.md holds Cycle: "
        f"{cycle}, so commits of the earlier cycle no longer count.")
    return report


def where() -> Path:
    """The folder that holds principles/ and checklist/, found from this script's own location."""
    for name in ("principles", "checklist"):
        if not (REPO / name).is_dir():
            raise InitError(f"{REPO / name} is missing; this script must run from a complete copy of the repository")
    return REPO


# --------------------------------------------------------------------- command

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InitError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="init_project.py", description="Start or adopt a project under the agentic-principles skill.")
    parser.add_argument("folder", nargs="?", help="the project folder (with --size and --method)")
    parser.add_argument("--size", help="small or full")
    parser.add_argument("--method", help="normal or sub-agent")
    parser.add_argument("--adopt-at", type=int, metavar="N", help="adopt an existing project: stages below N are adopted")
    parser.add_argument("--update-checks", metavar="FOLDER", help="replace the copied check scripts, keeping .bak files")
    parser.add_argument("--new-cycle", metavar="FOLDER", help="archive STAGES.md and start a fresh one")
    parser.add_argument("--where", action="store_true", help="print the folder holding principles/ and checklist/")
    return parser


def _print_report(report: Report) -> None:
    for title, items in (("created", report.created), ("updated", report.updated), ("backup made", report.backups),
                         ("kept (already there, not touched)", report.kept)):
        for item in items:
            print(f"{title}: {item}")
    for note in report.notes:
        print(f"note: {note}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
        modes = [m for m in (args.where, args.update_checks, args.new_cycle) if m]
        if len(modes) > 1 or (modes and (args.folder or args.size or args.method or args.adopt_at is not None)):
            raise InitError("--where, --update-checks and --new-cycle each stand alone")
        if args.where:
            print(where())
        elif args.update_checks:
            _print_report(update_checks(args.update_checks))
        elif args.new_cycle:
            _print_report(new_cycle(args.new_cycle))
        else:
            if not (args.folder and args.size and args.method):
                raise InitError("usage: init_project.py <folder> --size small|full --method normal|sub-agent "
                                "[--adopt-at N]")
            _print_report(init(args.folder, args.size, args.method, args.adopt_at))
    except InitError as error:
        print(f"init_project.py: {error}", file=sys.stderr)
        return 2
    except SystemExit as stop:                                # --help
        return int(stop.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
