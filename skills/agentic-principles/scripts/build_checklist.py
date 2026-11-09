"""Builds checklist/checklist.json from the engineering checklist files (stub: not written yet)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_gates  # noqa: E402

AREA_FILES = {"testing.md": "TEST", "security.md": "SEC", "dependencies.md": "DEP",
              "operations.md": "OPS", "data.md": "DATA", "ai-systems.md": "AI"}
TRAITS = set(check_gates.TRAIT_RULES) | {"personal-data"}


def parse_items(text: str) -> list[dict]:
    return []


def item_problems(text: str, companions: set[str]) -> list[str]:
    return []


def build(root) -> list[dict]:
    return []


def main(argv: list[str] | None = None) -> int:
    return 0


if __name__ == "__main__":
    sys.exit(main())
