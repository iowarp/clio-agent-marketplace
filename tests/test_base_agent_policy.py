"""Contract tests for the marketplace-owned Base Agent."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "base-agent"


class BaseAgentPolicyTests(unittest.TestCase):
    """Keep the former internal agent's useful behavior in marketplace data."""

    def test_manifest_identifies_the_configurable_general_agent(self) -> None:
        """The package describes a real default agent, not an internal fallback."""

        manifest = (ROOT / "AGENT.md").read_text(encoding="utf-8")

        self.assertIn("id: base-agent", manifest)
        self.assertIn("title: Base Agent", manifest)
        self.assertIn("version: 0.2.0", manifest)
        self.assertIn("without an internal fallback", manifest)

    def test_root_keeps_all_native_workspace_tools(self) -> None:
        """Base Agent retains the complete native tool surface of the removed agent."""

        expert = (ROOT / "experts" / "base.md").read_text(encoding="utf-8")

        for tool in ("shell_bash", "fs_read_file", "fs_propose_edit", "fs_apply_edit_write"):
            self.assertIn(f"  - {tool}\n", expert)

    def test_root_preserves_grounding_and_failure_policy(self) -> None:
        """The useful CLIO chat rules now live in the marketplace definition."""

        prose = " ".join(
            (ROOT / "experts" / "base.md").read_text(encoding="utf-8").split()
        )

        self.assertIn("Handle ordinary conversation directly and concisely", prose)
        self.assertIn("Never infer file contents", prose)
        self.assertIn("Treat tool results as observations", prose)
        self.assertIn("never claim the task succeeded", prose)
        self.assertIn("Ask one focused follow-up", prose)
        self.assertIn("Respect the session's execution and confirmation policies", prose)

    def test_root_declares_no_workflow_state_ontology(self) -> None:
        """Base Agent keeps its answer-only contract in marketplace data."""

        expert = (ROOT / "experts" / "base.md").read_text(encoding="utf-8")

        self.assertIn("structured_outputs:\n  workflow_state: false\n", expert)


if __name__ == "__main__":
    unittest.main()
