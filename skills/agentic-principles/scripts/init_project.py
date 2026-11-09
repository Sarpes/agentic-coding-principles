"""Project setup: stub for the red commit (replaced by the implementation in the next commit)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class InitError(Exception):
    """A bad argument or an unusable folder; the command exits with code 2."""


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def init(target, size, method, adopt_at=None) -> Report:
    return Report()


def claude_block(existing: str) -> str:
    return existing


def update_checks(target) -> Report:
    return Report()


def new_cycle(target) -> Report:
    return Report()


def where() -> Path:
    return Path(".")


def main(argv=None) -> int:
    return 0
