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
