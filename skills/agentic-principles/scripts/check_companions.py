"""Companion check: reports which skills, agents and commands named in companions.json are not installed or not enabled.

Usage: python check_companions.py [Claude folder]   (default: the .claude folder in the home directory)
Exit code: always 0. The report lists what is missing; the conductor then uses each row's fallback.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KINDS = ("skill", "agent", "command", "builtin", "local")
COMPANIONS = Path(__file__).resolve().parent.parent / "companions.json"
NOT_LOOKED_UP = ("builtin", "local")


def load(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mapping_problems(rows: list[dict]) -> list[str]:
    problems = []
    seen = set()
    for n, r in enumerate(rows, 1):
        label = f"row {n} ({r.get('capability', '?')})"
        if r.get("capability") in seen:
            problems.append(f"{label}: capability repeated")
        seen.add(r.get("capability"))
        if not str(r.get("fallback", "")).strip():
            problems.append(f"{label}: fallback is blank")
        stages = r.get("stages")
        if not stages or not all(isinstance(s, int) and 0 <= s <= 7 for s in stages):
            problems.append(f"{label}: stages must be whole numbers from 0 to 7")
        kind = r.get("kind")
        primary = str(r.get("primary", ""))
        if kind not in KINDS:
            problems.append(f"{label}: unknown kind {kind!r}")
        elif kind in ("skill", "agent") and not _plugin_name(primary):
            problems.append(f"{label}: {kind} must be written plugin:name, got {primary!r}")
        elif kind == "command" and not (primary.startswith("/") and _plugin_name(primary[1:])):
            problems.append(f"{label}: command must be written /plugin:command, got {primary!r}")
    return problems


def _plugin_name(text: str) -> bool:
    plugin, sep, name = text.partition(":")
    return bool(sep and plugin and name and "/" not in text)


def _version_key(folder: Path) -> tuple:
    return (tuple(int(d) for d in re.findall(r"\d+", folder.name)), folder.name)


def _frontmatter_name(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        key, _, value = line.partition(":")
        if key.strip() == "name" and value.strip():
            return value.strip().strip("\"'")
    return None


def installed(plugins_dir: Path, settings: Path) -> set[str]:
    try:
        enabled = json.loads(Path(settings).read_text(encoding="utf-8")).get("enabledPlugins", {})
    except (OSError, ValueError, AttributeError):
        return set()
    found: set[str] = set()
    for key, on in enabled.items():
        plugin, _, market = key.partition("@")
        if on is not True or not market:
            continue
        versions = [
            d for d in (Path(plugins_dir) / "cache" / market / plugin).glob("*")
            if d.is_dir() and not d.name.startswith("temp_git_")
        ]
        if not versions:
            continue
        newest = max(versions, key=_version_key)
        for skill in newest.rglob("SKILL.md"):
            name = _frontmatter_name(skill)
            if name:
                found.add(f"{plugin}:{name}")
        found.update(f"{plugin}:{p.stem}" for p in (newest / "agents").glob("*.md"))
        found.update(f"/{plugin}:{p.stem}" for p in (newest / "commands").glob("*.md"))
    return found


def _names(row: dict) -> list[str]:
    return [row["primary"], *row.get("also", [])]


def missing(rows: list[dict], available: set[str]) -> list[str]:
    out: list[str] = []
    for r in rows:
        if r["kind"] in NOT_LOOKED_UP:
            continue
        for name in _names(r):
            if name not in available and name not in out:
                out.append(name)
    return out


def report(rows: list[dict], available: set[str]) -> list[str]:
    needs: dict[str, list[str]] = {}
    for r in rows:
        if r["kind"] not in NOT_LOOKED_UP and r.get("requires"):
            needs[r["primary"]] = r["requires"]
    absent = missing(rows, available)
    lines = []
    for name in absent:
        extra = f" (needs the {', '.join(needs[name])} tool in the session)" if name in needs else ""
        lines.append(f"MISSING {name}{extra}: the fallback in companions.json applies")
    for name, tools in needs.items():
        if name not in absent:
            lines.append(f"installed {name}: needs the {', '.join(tools)} tool in the session (not checkable here)")
    if not absent:
        lines.insert(0, "all mapped companions are installed and enabled")
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    claude = Path(args[0]) if args else Path.home() / ".claude"
    rows = load(COMPANIONS)
    for line in report(rows, installed(claude / "plugins", claude / "settings.json")):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
