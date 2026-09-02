"""Structural contract tests for the marketplace-owned Base Agent.

These assert the *parsed* blueprint declaration, not the wording of its prose:
a pack is data the runtime loads, so the policy worth enforcing is that the
frontmatter parses, points at a real root expert, declares a well-formed tool
surface, and makes its structured-output posture explicit.
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1] / "base-agent"

_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_MAPPING_ITEM = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:(?:\s|$)")


@dataclass(frozen=True)
class _Line:
    """One significant frontmatter line with its indentation depth."""

    number: int
    indent: int
    text: str


def _scalar(text: str) -> Any:
    """Coerce one YAML scalar (or inline flow sequence) to a Python value."""
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(part) for part in inner.split(",")] if inner else []
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "~", ""}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _significant_lines(block: str) -> list[_Line]:
    """Return frontmatter lines with blanks and whole-line comments removed."""
    lines: list[_Line] = []
    for number, raw in enumerate(block.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        leading = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise ValueError(f"line {number}: tab indentation is not valid YAML")
        lines.append(_Line(number=number, indent=len(leading), text=stripped))
    return lines


def _parse_sequence(lines: list[_Line], start: int, indent: int) -> tuple[list[Any], int]:
    """Parse a block sequence of scalars, returning its items and the next index."""
    items: list[Any] = []
    index = start
    while index < len(lines) and lines[index].indent == indent:
        line = lines[index]
        if not line.text.startswith("- "):
            break
        item = line.text[2:].strip()
        if _MAPPING_ITEM.match(item):
            raise ValueError(f"line {line.number}: mappings inside sequences are unsupported")
        items.append(_scalar(item))
        index += 1
    return items, index


def _parse_mapping(lines: list[_Line], start: int, indent: int) -> tuple[dict[str, Any], int]:
    """Parse a block mapping at ``indent``, returning it and the next index."""
    mapping: dict[str, Any] = {}
    index = start
    while index < len(lines) and lines[index].indent >= indent:
        line = lines[index]
        if line.indent > indent:
            raise ValueError(f"line {line.number}: unexpected indentation")
        key, separator, rest = line.text.partition(":")
        if not separator:
            raise ValueError(f"line {line.number}: unsupported frontmatter syntax")
        name = key.strip()
        index += 1
        if rest.strip():
            mapping[name] = _scalar(rest)
            continue
        if index >= len(lines):
            mapping[name] = None
            continue
        following = lines[index]
        if following.text.startswith("- ") and following.indent >= indent:
            mapping[name], index = _parse_sequence(lines, index, following.indent)
        elif following.indent > indent:
            mapping[name], index = _parse_mapping(lines, index, following.indent)
        else:
            mapping[name] = None
    return mapping, index


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse the YAML frontmatter fenced by ``---`` at the top of a pack file.

    Deliberately a strict subset (nested mappings, scalar block/flow sequences,
    comments): anything it does not understand raises instead of silently
    yielding a partial mapping that would make a policy assertion vacuous.
    """
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing opening frontmatter fence")
    for offset, line in enumerate(lines[1:], start=1):
        if line.strip() != "---":
            continue
        significant = _significant_lines("\n".join(lines[1:offset]))
        mapping, consumed = _parse_mapping(significant, 0, 0)
        if consumed != len(significant):
            raise ValueError(f"{path}: line {significant[consumed].number} left unparsed")
        return mapping
    raise ValueError(f"{path}: missing closing frontmatter fence")


class BaseAgentManifestTests(unittest.TestCase):
    """The pack manifest must be loadable data pointing at a real expert."""

    def setUp(self) -> None:
        self.manifest = parse_frontmatter(ROOT / "AGENT.md")

    def test_manifest_declares_the_agent_blueprint_identity(self) -> None:
        """The manifest parses and identifies itself as a v1 agent blueprint."""
        self.assertEqual(self.manifest["id"], "base-agent")
        self.assertEqual(self.manifest["blueprint"], {"format": "agent-blueprint-v1"})
        self.assertIsInstance(self.manifest["title"], str)
        self.assertTrue(self.manifest["title"].strip())

    def test_manifest_version_is_semver(self) -> None:
        """The version must be releasable semver; its value is free to move."""
        version = self.manifest["version"]
        self.assertIsInstance(version, str)
        self.assertRegex(version, _SEMVER)

    def test_root_expert_resolves_to_a_declared_expert_file(self) -> None:
        """``root_expert`` names an expert this manifest actually ships."""
        root_expert = self.manifest["root_expert"]
        experts = self.manifest["experts"]
        self.assertIsInstance(experts, list)
        self.assertTrue(experts)

        resolved = []
        for relative in experts:
            path = ROOT / relative
            self.assertTrue(path.is_file(), f"declared expert file is missing: {relative}")
            resolved.append(parse_frontmatter(path)["id"])

        self.assertIn(root_expert, resolved)


class BaseAgentRootExpertTests(unittest.TestCase):
    """The root expert must declare a usable, explicit runtime contract."""

    def setUp(self) -> None:
        manifest = parse_frontmatter(ROOT / "AGENT.md")
        self.expert_path = ROOT / next(
            relative
            for relative in manifest["experts"]
            if parse_frontmatter(ROOT / relative)["id"] == manifest["root_expert"]
        )
        self.expert = parse_frontmatter(self.expert_path)

    def test_expert_declares_a_react_module_over_a_typed_signature(self) -> None:
        """The agent is a react loop answering into a typed ``answer`` field."""
        self.assertEqual(self.expert["module"], {"kind": "react"})
        signature = self.expert["signature"]
        self.assertIn("question", signature["inputs"])
        self.assertIn("answer", signature["outputs"])

    def test_declared_tools_are_a_well_formed_surface(self) -> None:
        """Tool names are non-empty, unique, and valid runtime identifiers.

        The native tool catalog lives in the clio-agent runtime, not in this
        data-only repository, so there is no name list to resolve against here;
        the declaration is checked structurally instead.
        """
        tools = self.expert["tools"]
        self.assertIsInstance(tools, list)
        self.assertTrue(tools, "the root expert must declare at least one tool")
        self.assertEqual(len(tools), len(set(tools)), "duplicate tool declaration")
        for tool in tools:
            self.assertIsInstance(tool, str)
            self.assertRegex(tool, _TOOL_NAME)

    def test_expert_declares_workflow_state_structured_output_disabled(self) -> None:
        """Base Agent opts out of workflow chrome explicitly, not by omission."""
        structured_outputs = self.expert["structured_outputs"]
        self.assertIsInstance(structured_outputs, dict)
        self.assertIn("workflow_state", structured_outputs)
        self.assertIs(structured_outputs["workflow_state"], False)


if __name__ == "__main__":
    unittest.main()
