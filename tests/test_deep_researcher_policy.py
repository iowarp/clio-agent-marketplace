"""Contract tests for the adaptive Deep Researcher coordination policy."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "deep-researcher"


def _prose(relative_path: str) -> str:
    """Return normalized Markdown prose from one Deep Researcher source file."""

    return " ".join((ROOT / relative_path).read_text(encoding="utf-8").split())


class DeepResearcherPolicyTests(unittest.TestCase):
    """Lock adaptive fan-out and committed-wait behavior."""

    def test_coordinator_uses_one_committed_wait_per_batch(self) -> None:
        """Prevent short polling ladders from returning to research runs."""

        expert = _prose("experts/main.md")

        self.assertIn("one committed `wait_agent_tasks` call", expert)
        self.assertIn("omits `timeout_s`", expert)
        self.assertIn("until every requested child is terminal", expert)
        self.assertIn("do not create a ladder of short waits", expert)
        self.assertNotIn("requires a finite `timeout_s`", expert)
        self.assertNotIn("poll or wait again", expert)

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
