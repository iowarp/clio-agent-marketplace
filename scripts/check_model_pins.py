#!/usr/bin/env python3
"""Reject undocumented model overrides in marketplace pack frontmatter."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Every frontmatter spelling clio-agent turns into a model pin
# (clio_agent/gact/expert_packs.py): an expert's ``model`` or
# ``default_model``, else the blueprint's ``defaults.model``.
_VALUE = r"\s*:\s*(?P<model>[^#]+?)\s*(?:#.*)?$"
_TOP_LEVEL_PIN = re.compile(r"^(?P<key>model)" + _VALUE)
_DEFAULT_MODEL_PIN = re.compile(r"^\s*(?P<key>default_model)" + _VALUE)
_NESTED_MODEL_PIN = re.compile(r"^\s+(?P<key>model)" + _VALUE)
_DEFAULTS_BLOCK = re.compile(r"^defaults\s*:\s*(?:#.*)?$")
_DEFAULTS_FLOW = re.compile(r"^defaults\s*:\s*\{(?P<body>[^}]*)\}")
_FLOW_MODEL = re.compile(r"(?:^|,)\s*model\s*:\s*(?P<model>[^,]+?)\s*(?=,|$)")
# Values the loader treats as "no pin" (it takes the first truthy key).
_UNSET = {"", "''", '""', "null", "~"}
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
    key: str = "default_model"


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


def _pin_on_line(line: str, in_defaults: bool) -> tuple[str, str] | None:
    """Return ``(key, model)`` when this frontmatter line pins a model."""
    for pattern, key in (
        (_TOP_LEVEL_PIN, "model"),
        (_DEFAULT_MODEL_PIN, "default_model"),
    ):
        match = pattern.match(line)
        if match is not None:
            return key, match.group("model")
    if in_defaults:
        match = _NESTED_MODEL_PIN.match(line)
        if match is not None:
            return "defaults.model", match.group("model")
    flow = _DEFAULTS_FLOW.match(line)
    if flow is not None:
        match = _FLOW_MODEL.search(flow.group("body"))
        if match is not None:
            return "defaults.model", match.group("model")
    return None


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
        in_defaults = False
        for index, line in enumerate(lines[1:end], start=1):
            if line and not line[0].isspace() and not line.startswith("#"):
                in_defaults = _DEFAULTS_BLOCK.match(line) is not None
            pin = _pin_on_line(line, in_defaults)
            if pin is None:
                continue
            key, raw_model = pin
            if raw_model.strip() in _UNSET:
                continue
            if _has_adjacent_justification(lines, index, end):
                continue
            violations.append(
                ModelPinViolation(
                    path=path,
                    line=index + 1,
                    model=raw_model.strip().strip("'\""),
                    key=key,
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
            f"{violation.key}={violation.model!r} requires an adjacent "
            "# model-pin-justification: ... comment"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
