#!/usr/bin/env python3
"""Reject undocumented model overrides in marketplace pack frontmatter."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

_PIN_PATTERN = re.compile(r"^\s*default_model\s*:\s*(?P<model>[^#]+?)\s*(?:#.*)?$")
_JUSTIFICATION_PATTERN = re.compile(
    r"^\s*#\s*model-pin-justification\s*:\s*\S.*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ModelPinViolation:
    """One undocumented model override found in active YAML frontmatter."""

    path: Path
    line: int
    model: str


def _frontmatter_end(lines: Sequence[str]) -> int | None:
    """Return the closing frontmatter line index, or ``None`` when absent."""
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    return None


def _has_adjacent_justification(lines: Sequence[str], index: int, end: int) -> bool:
    """Return whether a pin has the required adjacent explanatory comment."""
    adjacent = (candidate for candidate in (index - 1, index + 1) if 0 < candidate < end)
    return any(_JUSTIFICATION_PATTERN.match(lines[candidate]) for candidate in adjacent)


def find_unjustified_pins(root: Path) -> list[ModelPinViolation]:
    """Find active pack frontmatter pins without an adjacent justification."""
    violations: list[ModelPinViolation] = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        end = _frontmatter_end(lines)
        if end is None:
            continue
        for index, line in enumerate(lines[1:end], start=1):
            match = _PIN_PATTERN.match(line)
            if match is None or _has_adjacent_justification(lines, index, end):
                continue
            violations.append(
                ModelPinViolation(
                    path=path,
                    line=index + 1,
                    model=match.group("model").strip().strip("'\""),
                )
            )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Run the model-pin policy check and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    violations = find_unjustified_pins(root)
    if not violations:
        print("OK: marketplace model pins are absent or explicitly justified")
        return 0
    print("Undocumented marketplace model pins:")
    for violation in violations:
        print(
            f"  {violation.path.relative_to(root)}:{violation.line}: "
            f"default_model={violation.model!r} requires an adjacent "
            "# model-pin-justification: ... comment"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
