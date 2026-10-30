"""Tests for the marketplace model-pin policy."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_model_pins import find_unjustified_pins

_SUBAGENT = """from clio_agent.sdk import PromptFile, Subagent
from clio_agent.sdk.model import Prefers

reviewer = Subagent(
    "reviewer",
    prompt=PromptFile("prompt/subagents/reviewer.md"),
{extra}    prefers=Prefers(model="sonnet"),
)
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ModelPinPolicyTests(unittest.TestCase):
    """Exercise model-pin enforcement over agents, subagents and manifests."""

    def test_reports_unjustified_subagent_pin(self) -> None:
        """A subagent cannot silently override the session model."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root / "plugins" / "p" / "ai.iowarp.clio" / "subagents" / "reviewer.py",
                _SUBAGENT.format(extra=""),
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 7)
        self.assertEqual(violations[0].model, "sonnet")

    def test_accepts_adjacent_explicit_justification(self) -> None:
        """A documented exceptional pin remains mechanically auditable."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root / "plugins" / "p" / "ai.iowarp.clio" / "subagents" / "reviewer.py",
                _SUBAGENT.format(
                    extra="    # model-pin-justification: protocol qualification fixture\n"
                ),
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(violations, [])

    def test_reports_agent_class_and_manifest_pins(self) -> None:
        """Agent classes and plugin.json preferences are checked too."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root / "agents" / "a.py",
                "from clio_agent.sdk import Agent, Prefers\n\n"
                "class A(Agent):\n    id = 'a'\n    prefers = Prefers(provider='openai')\n",
            )
            _write(
                root / "plugins" / "p" / "plugin.json",
                json.dumps({"extensions": {"ai.iowarp.clio": {"prefers": {"model": "gpt"}}}}),
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(sorted(v.model for v in violations), ["gpt", "openai"])

    def test_ignores_prose_and_effort_only_preferences(self) -> None:
        """Documentation and non-model preferences are not pins."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root / "plugins" / "p" / "README.md", "`Prefers(model='sonnet')`\n")
            _write(
                root / "agents" / "a.py",
                "from clio_agent.sdk import Prefers\n\nX = Prefers(effort='high', model='')\n",
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(violations, [])

    def test_reports_every_spelling_the_sdk_accepts(self) -> None:
        """from_dict, positional, ** and a prefers dict literal pin as surely as model=."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root / "plugins" / "p" / "ai.iowarp.clio" / "subagents" / "s.py",
                "from clio_agent.sdk.model import Prefers\n\n"
                "A = Prefers.from_dict({'model': 'from-dict'})\n"
                "B = Prefers('positional')\n"
                "C = Prefers(**{'provider': 'splat'})\n"
                "D = Subagent('d', prefers={'model': 'literal'})\n"
                "E = Prefers.from_dict(SAVED)\n"
                "F = Prefers(**SAVED)\n"
                "G = Prefers.from_dict({'effort': 'high'})\n"
                "H = Prefers('', '')\n",
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(
            [(v.line, v.model) for v in violations],
            [
                (3, "from-dict"),
                (4, "positional"),
                (5, "splat"),
                (6, "literal"),
                (7, "SAVED"),
                (8, "SAVED"),
            ],
        )

    def test_a_justification_covers_the_other_spellings(self) -> None:
        """The escape hatch works for from_dict as it does for model=."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root / "agents" / "a.py",
                "# model-pin-justification: exported backup keeps the user's choice\n"
                "P = Prefers.from_dict({'model': 'kept'})\n",
            )

            self.assertEqual(find_unjustified_pins(root), [])


if __name__ == "__main__":
    unittest.main()
