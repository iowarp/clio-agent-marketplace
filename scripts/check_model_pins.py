#!/usr/bin/env python3
"""Reject undocumented model pins in marketplace agents, subagents and plugins.

Every agent and subagent inherits the provider and model selected for the
session. A pin is a ``model`` or ``provider`` preference in ``agents/*.py`` or
a plugin's ``ai.iowarp.clio/**/*.py`` (a subagent's ``prefers``, a plugin
declaration's ``prefers``), in every spelling the clio-agent SDK accepts:
``Prefers(model=...)``, ``Prefers("model", "provider")`` (positional),
``Prefers(**{...})``, ``Prefers.from_dict({...})`` and a ``prefers={...}``
dict literal. A ``Prefers(**name)`` or ``Prefers.from_dict(name)`` whose value
the check cannot read is reported too. A ``prefers.model`` /
``prefers.provider`` in a plugin.json ``ai.iowarp.clio`` extension is a pin as
well. A pin is
allowed only with an adjacent ``# model-pin-justification: <reason>`` comment
(on the line before the call or on any line of it); a plugin.json pin cannot
carry a comment, so it is always reported.

Dependency-free: the Python files are parsed, never imported.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

PINNED_FIELDS = ("model", "provider")
_JUSTIFICATION_PATTERN = re.compile(r"#\s*model-pin-justification\s*:\s*\S", re.IGNORECASE)


@dataclass(frozen=True)
class ModelPinViolation:
    """One undocumented model or provider pin."""

    path: Path
    line: int
    model: str


def _python_files(root: Path) -> Iterator[Path]:
    agents = root / "agents"
    if agents.is_dir():
        yield from sorted(agents.glob("*.py"))
    plugins = root / "plugins"
    if plugins.is_dir():
        for path in sorted(plugins.glob("*/ai.iowarp.clio/**/*.py")):
            if "__pycache__" not in path.parts:
                yield path


def _named_prefers(node: ast.expr) -> bool:
    name = node.id if isinstance(node, ast.Name) else getattr(node, "attr", "")
    return name == "Prefers"


def _is_prefers(call: ast.Call) -> bool:
    return _named_prefers(call.func)


def _is_from_dict(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "from_dict"
        and _named_prefers(func.value)
    )


def _set(value: ast.expr) -> bool:
    """Whether a preference value pins something: empty constants do not."""
    return not (isinstance(value, ast.Constant) and not value.value)


def _dict_pins(node: ast.expr) -> list[ast.expr] | None:
    """Pinned values in a dict literal, or ``None`` when ``node`` cannot be read."""
    if not isinstance(node, ast.Dict):
        return None
    pins: list[ast.expr] = []
    for key, value in zip(node.keys, node.values, strict=True):
        if key is None:  # {**other}: unreadable
            return None
        if isinstance(key, ast.Constant) and key.value in PINNED_FIELDS and _set(value):
            pins.append(value)
    return pins


def _call_pins(call: ast.Call) -> list[ast.expr]:
    """The pinned values of one call; the call itself when a value is unreadable."""
    if _is_prefers(call):
        pins = [arg for arg in call.args[: len(PINNED_FIELDS)] if _set(arg)]
        for kw in call.keywords:
            if kw.arg in PINNED_FIELDS and _set(kw.value):
                pins.append(kw.value)
            elif kw.arg is None:
                read = _dict_pins(kw.value)
                pins.extend(read if read is not None else [kw.value])
        return pins
    if _is_from_dict(call) and call.args:
        read = _dict_pins(call.args[0])
        return read if read is not None else [call.args[0]]
    pins = []
    for kw in call.keywords:
        if kw.arg == "prefers" and isinstance(kw.value, ast.Dict):
            pins.extend(_dict_pins(kw.value) or [])
    return pins


def _python_pins(path: Path) -> Iterator[ModelPinViolation]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        pinned = _call_pins(node)
        if not pinned:
            continue
        first = node.lineno - 1
        last = (node.end_lineno or node.lineno) - 1
        window = lines[max(first - 1, 0) : last + 1]
        if any(_JUSTIFICATION_PATTERN.search(line) for line in window):
            continue
        value = pinned[0]
        model = value.value if isinstance(value, ast.Constant) else ast.unparse(value)
        yield ModelPinViolation(path=path, line=node.lineno, model=str(model))


def _manifest_pins(root: Path) -> Iterator[ModelPinViolation]:
    for path in sorted((root / "plugins").glob("*/plugin.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        ext = (data.get("extensions") or {}).get("ai.iowarp.clio") or {}
        prefers = ext.get("prefers") or {}
        for field in PINNED_FIELDS:
            if prefers.get(field):
                yield ModelPinViolation(path=path, line=0, model=str(prefers[field]))


def find_unjustified_pins(root: Path) -> list[ModelPinViolation]:
    """Find model or provider pins without an adjacent justification."""
    violations: list[ModelPinViolation] = []
    for path in _python_files(root):
        violations.extend(_python_pins(path))
    violations.extend(_manifest_pins(root))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """Run the model-pin policy check and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
            f"model={violation.model!r} requires an adjacent "
            "# model-pin-justification: ... comment"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
