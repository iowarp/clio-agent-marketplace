"""Contract tests for the adaptive Deep Researcher coordination policy."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "deep-researcher"


def _prose(relative_path: str) -> str:
    """Return normalized Markdown prose from one Deep Researcher source file."""

    return " ".join((ROOT / relative_path).read_text(encoding="utf-8").split())


class DeepResearcherPolicyTests(unittest.TestCase):
    """Lock adaptive fan-out and evidence-complete coordination behavior."""

    def test_coordinator_owns_tree_without_reauthoring_runtime_waits(self) -> None:
        """Runtime tool contracts, not this prompt, own wait and observe semantics."""

        expert = _prose("experts/main.md")

        self.assertIn("complete internal researcher-and-critic tree", expert)
        self.assertIn("collect every accepted child", expert)
        self.assertIn(
            "native tool contracts define collection and observation behavior", expert
        )
        self.assertNotIn("timeout_s", expert)
        self.assertNotIn("check_agent_tasks", expert)

    def test_research_breadth_and_rounds_remain_evidence_driven(self) -> None:
        """Keep the coordinator adaptive rather than imposing a worker quota."""

        expert = _prose("experts/main.md")

        self.assertIn("preselect a worker count", expert)
        self.assertIn("You may repeat `researcher` as many times as useful", expert)
        self.assertIn(
            "The number of audit and research rounds is determined by the evidence",
            expert,
        )

    def test_final_artifact_declares_only_used_and_cited_source_urls(self) -> None:
        """Keep the strict evidence graph aligned with the audited source ledger."""

        expert = _prose("experts/main.md")

        self.assertIn("Set `used` to the exact final fetched URL", expert)
        self.assertIn("every `USED_AND_CITED` source", expert)
        self.assertIn("Do not put `READ_NOT_USED`, `REJECTED`, `FETCH_FAILED`", expert)
        self.assertIn("tool execution proves which fetches actually ran", expert)


if __name__ == "__main__":
    unittest.main()
