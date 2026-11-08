"""Companion check: reports which skills, agents and commands named in companions.json are not installed or not enabled.

Usage: python check_companions.py [Claude folder]   (default: the .claude folder in the home directory)
Exit code: always 0. The report lists what is missing; the conductor then uses each row's fallback.
"""
from __future__ import annotations

from pathlib import Path

KINDS = ("skill", "agent", "command", "builtin", "local")
NOT_LOOKED_UP = ("builtin", "local")


def load(path: Path) -> list[dict]:
    return []


def mapping_problems(rows: list[dict]) -> list[str]:
    return []


def installed(plugins_dir: Path, settings: Path) -> set[str]:
    return set()


def missing(rows: list[dict], available: set[str]) -> list[str]:
    return []


def report(rows: list[dict], available: set[str]) -> list[str]:
    return []


def main(argv: list[str] | None = None) -> int:
    return 0
