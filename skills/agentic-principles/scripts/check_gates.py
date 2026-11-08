"""Signature stubs for the red phase: every function returns an empty result."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import NamedTuple

__version__ = "0.2.0"

STAGE_NAMES = ("0 Intake", "1 Design", "2 Plan", "3 Build", "4 Verify", "5 Ship", "6 Own", "7 Retro")
SOURCE_EXTENSIONS = ()
TRUST_LIMIT = ""


class Problem(NamedTuple):
    file: str
    line: int
    message: str


class GateError(Exception):
    pass


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
    traits: set[str] | None = None
    rows: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


class Override(NamedTuple):
    status: str
    stage: str
    reconfirmed: str


def tracked_files(root):
    return []


def parse_stages(text):
    return Stages()


def stage_problems(text, root, tracked, overrides, file="STAGES.md"):
    return []


def evidence_content_problems(stage, size, root, tracked, row, stages_first_commit):
    return []


def parse_overrides(text):
    return {}


def override_problems(text, root, stages, file="OVERRIDES.md"):
    return []


def check_project(root, today: date | None = None):
    return [], []


def main(argv=None):
    return 0
