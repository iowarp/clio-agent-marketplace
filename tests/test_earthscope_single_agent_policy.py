"""Contract tests for the reuse-first EarthScope Skills presentation policy."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "earthscope-single-agent"


def _read(relative_path: str) -> str:
    """Return one EarthScope Skills source file as UTF-8 text."""

    return (ROOT / relative_path).read_text(encoding="utf-8")


def _prose(relative_path: str) -> str:
    """Return Markdown prose with presentation-only whitespace normalized."""

    return " ".join(_read(relative_path).split())


class EarthScopeSingleAgentPolicyTests(unittest.TestCase):
    """Lock the scientist-facing A2UI and delegation behavior."""

    def test_root_contract_keeps_protocol_language_out_of_user_prompts(self) -> None:
        expert = _prose("experts/main.md")

        self.assertIn("The user does not need to request A2UI", expert)
        self.assertIn("Do not describe implementation topology to the user", expert)
        self.assertIn("Do not accumulate unrelated results into one large tabbed surface", expert)

    def test_station_ranking_requires_a_stage_local_interactive_map(self) -> None:
        acquire = _prose("skills/acquire-earthscope-gnss/SKILL.md")

        self.assertIn("create or update `earthscope-stations` immediately", acquire)
        self.assertIn("otherwise prefer the interactive map", acquire)
        self.assertIn("Do not wait until the end of the turn", acquire)

    def test_interactive_time_series_is_primary_and_png_is_not_embedded(self) -> None:
        visualize = _prose("skills/visualize-earthscope-gnss/SKILL.md")

        self.assertIn("The primary plot is a live, data-backed A2UI chart", visualize)
        self.assertIn("using exactly one primary `clio.time-series.v1`", visualize)
        self.assertIn("Generate a static PNG only when the user explicitly asks", visualize)
        self.assertIn("Never place the static image below, beside, or inside the interactive chart", visualize)

    def test_parallel_region_skill_remains_explicit_visible_delegation(self) -> None:
        expert = _prose("experts/main.md")
        compare = _prose("skills/compare-earthscope-coverage/SKILL.md")
        delegate = _prose("skills/delegate-earthscope-region/SKILL.md")

        self.assertIn("load `compare-earthscope-coverage` before any regional resolution", expert)
        self.assertIn("is an action, not documentation", expert)
        self.assertIn("Never invoke such a skill speculatively", expert)
        self.assertLess(
            _read("experts/main.md").index("  - compare-earthscope-coverage"),
            _read("experts/main.md").index("  - delegate-earthscope-region"),
        )
        self.assertIn('load_skill(skill_id="delegate-earthscope-region"', compare)
        self.assertIn("Collect the returned task ids with `wait_agent_tasks`", compare)
        self.assertIn("Never delegate all regions", compare)
        self.assertIn("literal cleaned catalog path", compare)
        self.assertIn("Call `pandas_filter_data`", compare)
        self.assertIn("Never substitute the raw staged path", compare)
        self.assertIn("never treat profiling the raw file as normalization", compare)
        self.assertIn("effect: spawn_subagent_with_skill", delegate)
        self.assertIn("You are already running this skill", delegate)
        self.assertIn("Do not call `load_skill`, `spawn_skill_task`", delegate)


if __name__ == "__main__":
    unittest.main()
