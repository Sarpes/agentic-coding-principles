"""Documentation gate: checks DECISIONS.md, AI-Agents.md and (if present) REQUIREMENTS.md.

Usage: python checks/check_docs.py [repository folder]   (default: the current directory)
Exit codes: 0 no problems, 1 problems found (printed as FILE:LINE: message), 2 usage error (more than one argument, or not a directory).
Line numbers are 1-based lines of the original file; 0 means the problem concerns the whole file.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


class Problem(NamedTuple):
    file: str
    line: int
    message: str


DECISION_FIELDS = ("Context", "Options considered", "Chosen", "Why", "Rejected",
                   "Cost / trade-off", "What would make you change it")
AI_LOG_FIELDS = ("Prompt (or summary of it)", "What the AI produced", "What I kept",
                 "What I changed or rejected, and why",
                 "Where the AI was wrong, and how I noticed")
SECTIONS = ("Assumptions", "Not done (and why)")
REQUIREMENT_COLUMNS = ("ID", "Requirement", "Decision", "Test", "Evidence", "Status")
STATUSES = ("open", "met", "not done")

FIELD = re.compile(r"^- \*\*(.+?):\*\*[ \t]*(.*)$")
# A bare value that gives no reason: nothing, None, N/A, TBD, TODO, a dash or an ellipsis.
PLACEHOLDER = re.compile(r"(none|n/?a|tbd|todo|-|\.\.\.|…)?\.?", re.I)
FENCE = re.compile(r"^ {0,3}```")
ANY_HEADING = re.compile(r"^#{1,3} ")
GROUPED = re.compile(r"^### (D\d+\s*[-–,]\s*D?\d+)")


def normalise(text: str) -> str:
    """Drop a byte-order mark and turn CRLF into LF."""
    return text.lstrip("﻿").replace("\r\n", "\n")


def prepare(text: str) -> list[str]:
    """Lines of the text with fenced code blocks blanked, so line numbers stay true."""
    lines = normalise(text).split("\n")
    inside = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            inside = not inside
            lines[i] = ""
        elif inside:
            lines[i] = ""
    return lines


def entries(lines: list[str], heading: re.Pattern) -> list[tuple[int, int, list[tuple[int, str]]]]:
    """(number, heading line, body lines) for each entry; a body runs to the next heading."""
    out = []
    for i, line in enumerate(lines):
        m = heading.match(line)
        if not m:
            continue
        body = []
        for j in range(i + 1, len(lines)):
            if ANY_HEADING.match(lines[j]):
                break
            body.append((j + 1, lines[j]))
        out.append((int(m.group(1)), i + 1, body))
    return out


def numbering_problems(items, prefix: str, file: str) -> list[Problem]:
    nums = [n for n, _, _ in items]
    for position, (n, heading_line, _) in enumerate(items):
        if n != position + 1:
            listed = ", ".join(f"{prefix}{x}" for x in nums)
            return [Problem(file, heading_line,
                            f"numbering is {listed}; expected {prefix}1..{prefix}{len(nums)} in order")]
    return []


def near_miss(label: str, body: list[tuple[int, str]]):
    """First body line that looks like the label but is not written exactly (case, colon outside bold)."""
    pattern = re.compile(rf"^\s*(?:[-*]\s*)?\**\s*{re.escape(label)}\s*\**\s*:\s*\**", re.I)
    for number, line in body:
        if pattern.match(line):
            return number, line.strip()
    return None


def field_problems(name: str, heading_line: int, body, required, strict: bool, file: str) -> list[Problem]:
    found: dict[str, str] = {}
    for _, line in body:
        m = FIELD.match(line)
        if m:
            found[m.group(1).strip()] = m.group(2).strip()
    problems = []
    for label in required:
        exact = f"- **{label}:**"
        if label not in found:
            hit = near_miss(label, body)
            if hit:
                problems.append(Problem(file, hit[0],
                                        f"{name}: missing '{exact}' (found '{hit[1]}'; expected exactly '{exact}')"))
            else:
                problems.append(Problem(file, heading_line, f"{name}: missing '{exact}'"))
        elif strict and PLACEHOLDER.fullmatch(found[label]):
            problems.append(Problem(file, heading_line,
                                    f"{name}: '{label}' is empty or a placeholder "
                                    "(write 'None: <reason>' if nothing applies)"))
        elif not found[label]:
            problems.append(Problem(file, heading_line, f"{name}: '{label}' is empty"))
    return problems


def heading_form_problems(lines: list[str], like: re.Pattern, exact: re.Pattern,
                          expected: str, file: str) -> list[Problem]:
    """Heading lines that look like an entry heading but are not written in the exact form."""
    return [Problem(file, i + 1, f"heading '{line.strip()}' is not in the form '{expected}'")
            for i, line in enumerate(lines)
            if like.match(line) and not exact.match(line) and not GROUPED.match(line)]


def decisions_problems(text: str, file: str = "DECISIONS.md") -> list[Problem]:
    lines = prepare(text)
    items = entries(lines, re.compile(r"^### D(\d+)\."))
    problems = [Problem(file, i + 1, f"{m.group(1)}: one decision per entry (split the grouped heading)")
                for i, line in enumerate(lines) if (m := GROUPED.match(line))]
    problems += heading_form_problems(lines, re.compile(r"^#{1,6}\s*D\d+"), re.compile(r"^### D\d+\. "),
                                      "### D<number>. <title>", file)
    problems += numbering_problems(items, "D", file)
    for n, heading_line, body in items:
        problems += field_problems(f"D{n}", heading_line, body, DECISION_FIELDS, True, file)
    for section in SECTIONS:
        if not any(re.fullmatch(rf"## {re.escape(section)}[ \t]*", line) for line in lines):
            problems.append(Problem(file, 0, f"missing section '## {section}'"))
    if not items:
        problems.append(Problem(file, 0, "no decision yet (### D1. ...)"))
    return problems


def ai_log_problems(text: str, file: str = "AI-Agents.md") -> list[Problem]:
    lines = prepare(text)
    items = entries(lines, re.compile(r"^### (\d+)\."))
    # 1-3 digits only, so a heading such as "### 2026 plans" is not mistaken for an entry
    problems = heading_form_problems(lines, re.compile(r"^#{1,6}\s*\d{1,3}(?:[.)]|\s|$)"),
                                     re.compile(r"^### \d+\. "), "### <number>. <title>", file)
    problems += numbering_problems(items, "", file)
    for n, heading_line, body in items:
        problems += field_problems(f"entry {n}", heading_line, body, AI_LOG_FIELDS, False, file)
    if not items:
        problems.append(Problem(file, 0, "no entry yet (### 1. ...)"))
    return problems


def split_row(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", inner)]


def requirements_problems(text: str, file: str = "REQUIREMENTS.md") -> list[Problem]:
    rows = [(i + 1, line) for i, line in enumerate(prepare(text)) if line.lstrip().startswith("|")]
    if not rows:
        return [Problem(file, 0, "no requirements table found (columns: " + " | ".join(REQUIREMENT_COLUMNS) + ")")]
    head_line, head = rows[0]
    if [c.lower() for c in split_row(head)] != [c.lower() for c in REQUIREMENT_COLUMNS]:
        return [Problem(file, head_line, "table columns must be exactly: " + " | ".join(REQUIREMENT_COLUMNS))]
    problems = []
    data = rows[1:]
    if data and all(re.fullmatch(r":?-+:?", c) for c in split_row(data[0][1])):
        data = data[1:]                                   # the alignment row under the header
    for number, line in data:
        cells = split_row(line)
        if len(cells) != len(REQUIREMENT_COLUMNS):
            problems.append(Problem(file, number,
                                    f"row has {len(cells)} cells; expected {len(REQUIREMENT_COLUMNS)}"))
            continue
        name = cells[0] or f"line {number}"
        empty = [col for col, cell in zip(REQUIREMENT_COLUMNS, cells) if not cell]
        for col in empty:
            problems.append(Problem(file, number, f"{name}: cell '{col}' is empty"))
        values = dict(zip(REQUIREMENT_COLUMNS, cells))
        status = values["Status"]
        if status and status not in STATUSES:
            problems.append(Problem(file, number,
                                    f"{name}: Status '{status}' must be one of: {', '.join(STATUSES)}"))
        elif status == "met":
            for col in ("Test", "Evidence"):
                if values[col] == "-":
                    problems.append(Problem(file, number, f"{name}: Status is met but {col} is '-'"))
    return problems


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def check_repo(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    root = Path(root)
    for name, rule in (("DECISIONS.md", decisions_problems), ("AI-Agents.md", ai_log_problems)):
        path = root / name
        if path.is_file():
            problems += rule(read(path), name)
        else:
            problems.append(Problem(name, 0, "file is missing"))
    requirements = root / "REQUIREMENTS.md"
    if requirements.is_file():
        problems += requirements_problems(read(requirements), "REQUIREMENTS.md")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: check_docs.py [repository folder]", file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path.cwd()
    if not root.is_dir():
        print(f"check_docs.py: not a directory: {root}", file=sys.stderr)
        return 2
    problems = check_repo(root)
    for p in problems:
        print(f"{p.file}:{p.line}: {p.message}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
