"""Tests for the marketplace model-pin policy."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_model_pins import find_unjustified_pins


class ModelPinPolicyTests(unittest.TestCase):
    """Exercise frontmatter-only model-pin enforcement."""

    def test_reports_unjustified_frontmatter_pin(self) -> None:
        """A pack cannot silently override the session model."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "pack" / "experts" / "main.md"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                "---\nid: main\ndefault_model: sonnet\n---\nBody\n",
                encoding="utf-8",
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 3)
        self.assertEqual(violations[0].model, "sonnet")

    def test_accepts_adjacent_explicit_justification(self) -> None:
        """A documented exceptional pin remains mechanically auditable."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "pack" / "AGENT.md"
            pack.parent.mkdir(parents=True)
            pack.write_text(
                "---\nid: pack\n"
                "# model-pin-justification: protocol qualification fixture\n"
                "default_model: fixture-model\n---\n",
                encoding="utf-8",
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(violations, [])

    def _violations(self, frontmatter: str) -> list:
        """Run the checker over one AGENT.md carrying ``frontmatter``."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "pack" / "AGENT.md"
            pack.parent.mkdir(parents=True)
            pack.write_text(f"---\n{frontmatter}---\nBody\n", encoding="utf-8")
            return find_unjustified_pins(root)

    def test_reports_bare_model_key(self) -> None:
        """The loader honours ``model:`` exactly like ``default_model:`` (#62)."""
        violations = self._violations("id: main\nmodel: sonnet\n")

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 3)
        self.assertEqual(violations[0].model, "sonnet")
        self.assertEqual(violations[0].key, "model")

    def test_reports_model_under_blueprint_defaults(self) -> None:
        """``defaults.model`` pins every expert of the blueprint."""
        violations = self._violations(
            "id: pack\ndefaults:\n  prompt_profile: heavy\n  model: opus\n"
        )

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 5)
        self.assertEqual(violations[0].key, "defaults.model")
        self.assertEqual(violations[0].model, "opus")

    def test_reports_model_in_flow_style_defaults(self) -> None:
        """The one-line mapping form pins just the same."""
        violations = self._violations(
            "id: pack\ndefaults: {prompt_profile: heavy, model: 'opus'}\n"
        )

        self.assertEqual([(v.key, v.model) for v in violations], [("defaults.model", "opus")])

    def test_accepts_justified_bare_model_key(self) -> None:
        """The justification escape hatch covers every pin spelling."""
        violations = self._violations(
            "id: pack\n# model-pin-justification: protocol fixture\nmodel: fixture\n"
        )

        self.assertEqual(violations, [])

    def test_ignores_model_keys_the_loader_does_not_read(self) -> None:
        """A ``model:`` nested under any other block is not a pin."""
        violations = self._violations(
            "id: pack\nworkflow_state:\n  model: sonnet\ndefaults:\n"
            "  prompt_profile: heavy\nmodel_family: claude\n"
        )

        self.assertEqual(violations, [])

    def test_ignores_unset_model_values(self) -> None:
        """An empty or null value is not a pin: the loader skips falsy keys."""
        violations = self._violations("id: pack\nmodel: ''\ndefault_model: null\n")

        self.assertEqual(violations, [])

    def test_ignores_body_examples_and_non_frontmatter_files(self) -> None:
        """Documentation prose must not be mistaken for active configuration."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body_example = root / "pack" / "README.md"
            body_example.parent.mkdir(parents=True)
            body_example.write_text(
                "# Example\n\n`default_model: sonnet` is discouraged.\n",
                encoding="utf-8",
            )

            violations = find_unjustified_pins(root)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
