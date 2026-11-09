"""Builds checklist/checklist.json from the engineering checklist files, after checking every item.

Usage: python build_checklist.py [--check] [repository folder]   (default: the current directory)
Without --check it writes checklist/checklist.json. With --check it writes nothing and fails when the
file differs from what the checklist files say.
Exit codes: 0 done (or up to date), 1 problems in the items or a stale file (printed), 2 usage error.

Each item in checklist/<area>.md is a heading '### C-<AREA>-<n> <title>' followed by six fields written
'- **Label:** value'. The generated file holds only {"id", "applies_when"} per item, which is what
check_gates.py reads to decide which rows GO-LIVE.md needs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_gates  # noqa: E402

# File name to area code, in the order the items appear in checklist.json.
AREA_FILES = {"testing.md": "TEST", "security.md": "SEC", "dependencies.md": "DEP",
              "operations.md": "OPS", "data.md": "DATA", "ai-systems.md": "AI"}
FIELDS = ("Rule", "Why it matters", "Applies when", "How to validate", "Companion", "Source")
# The traits check_gates.py detects, plus the one only the owner can declare.
TRAITS = set(check_gates.TRAIT_RULES) | {"personal-data"}
CHECKLIST_DIR = "checklist"
OUTPUT = "checklist/checklist.json"
COMPANIONS_FILE = "skills/agentic-principles/companions.json"

ITEM_HEADING = re.compile(r"^### (C-([A-Z]+)-(\d+)) (\S.*?)[ \t]*$")
ITEM_LIKE = re.compile(r"^#{1,6}[ \t]*C-", re.I)
HTTPS = re.compile(r"https://\S+")


def parse_items(text: str) -> list[dict]:
    """Items in file order: {"id", "area", "number", "title", "line", "fields": {label: value}}."""
    lines = check_gates.clean_lines(text)
    items = []
    for i, line in enumerate(lines):
        m = ITEM_HEADING.match(line)
        if not m:
            continue
        fields: dict[str, str] = {}
        for later in lines[i + 1:]:
            if re.match(r"#{1,6} ", later):
                break
            f = check_gates.FIELD.match(later)
            if f and f.group(1).strip() not in fields:
                fields[f.group(1).strip()] = f.group(2).strip()
        items.append({"id": m.group(1), "area": m.group(2), "number": int(m.group(3)),
                      "title": m.group(4), "line": i + 1, "fields": fields})
    return items


def traits_of(value: str) -> list[str]:
    return [t.strip().lower() for t in value.split("+")]


def item_problems(text: str, companions: set[str]) -> list[str]:
    """Why the items in one checklist file are not acceptable, as 'line N: message' texts."""
    problems = []
    for number, line in enumerate(check_gates.clean_lines(text), start=1):
        if ITEM_LIKE.match(line) and not ITEM_HEADING.match(line):
            problems.append(f"line {number}: heading '{line.strip()}' is not in the form '### C-<AREA>-<n> <title>'")
    items = parse_items(text)
    if not items:
        problems.append("line 0: no items found (### C-<AREA>-<n> <title>)")
        return problems
    area = items[0]["area"]
    for position, found in enumerate(items, start=1):
        if found["id"] != f"C-{area}-{position}":
            problems.append(f"line {found['line']}: id {found['id']} is out of order; expected C-{area}-{position} "
                            "(one area per file, numbered from 1 without gaps)")
            break
    for found in items:
        problems += [f"line {found['line']}: {found['id']}: {message}"
                     for message in _field_problems(found["fields"], companions)]
    return problems


def _field_problems(fields: dict[str, str], companions: set[str]) -> list[str]:
    problems = []
    for label in FIELDS:
        if label not in fields:
            problems.append(f"missing '- **{label}:**'")
        elif not fields[label] or check_gates.PLACEHOLDER.fullmatch(fields[label]):
            if not (label == "Companion" and fields[label].lower() == "none"):
                problems.append(f"'{label}' is blank; say what it is")
    applies = fields.get("Applies when", "")
    if applies:
        names = traits_of(applies)
        if "always" in names and len(names) > 1:
            problems.append("'always' stands alone; do not join it with traits")
        for name in names:
            if name != "always" and name not in TRAITS:
                problems.append(f"unknown trait '{name}' in 'Applies when'; use 'always' or traits joined with + "
                                f"from: {', '.join(sorted(TRAITS))}")
    companion = fields.get("Companion", "")
    if companion and companion.lower() != "none" and companion not in companions:
        problems.append(f"companion '{companion}' is not in companions.json; name one from it or write 'none'")
    source = fields.get("Source", "")
    if source:
        if not HTTPS.search(source):
            problems.append("'Source' must hold an https:// address of the page read")
        elif not re.search(r"[A-Za-z]{3,}", HTTPS.sub("", source)):
            problems.append("'Source' holds only an address; name the source and the section too")
    return problems


def load_companions(root: Path) -> set[str]:
    """Every name in the companion mapping: each row's primary and its alternatives."""
    rows = json.loads((root / COMPANIONS_FILE).read_text(encoding="utf-8"))
    return {r["primary"] for r in rows} | {name for r in rows for name in r.get("also", [])}


def build(root) -> list[dict]:
    """[{"id", "applies_when": [traits]}] for every item; ValueError when any file is missing or has problems."""
    root = Path(root)
    companions = load_companions(root)
    rows, problems = [], []
    for name, area in AREA_FILES.items():
        path = root / CHECKLIST_DIR / name
        if not path.is_file():
            problems.append(f"{CHECKLIST_DIR}/{name}: file is missing")
            continue
        text = check_gates.normalise(path.read_text(encoding="utf-8"))
        found = item_problems(text, companions)
        items = parse_items(text)
        if items and items[0]["area"] != area:
            found.append(f"line {items[0]['line']}: items in {name} must use the area code {area}")
        problems += [f"{CHECKLIST_DIR}/{name}: {message}" for message in found]
        rows += [{"id": i["id"], "applies_when": traits_of(i["fields"].get("Applies when", ""))} for i in items]
    if problems:
        raise ValueError("\n".join(problems))
    return rows


def render(rows: list[dict]) -> str:
    return json.dumps(rows, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    if len(args) > 1:
        print("usage: python build_checklist.py [--check] [repository folder]", file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path.cwd()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    try:
        text = render(build(root))
    except ValueError as error:
        print(error)
        return 1
    target = root / OUTPUT
    if check:
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current is None or json.loads(current) != json.loads(text):
            print(f"{OUTPUT} is out of date; run: python skills/agentic-principles/scripts/build_checklist.py")
            return 1
        print(f"{OUTPUT} is up to date")
        return 0
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
