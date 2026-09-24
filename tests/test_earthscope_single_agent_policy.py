"""Contract tests for the reuse-first EarthScope Skills presentation policy."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.test_base_agent_policy import parse_frontmatter

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
        self.assertIn("Load the catalog skill `a2ui-catalog-earthscope-stations`", acquire)
        self.assertIn("one `StationMap` showing every ranked point", acquire)
        self.assertIn(
            "one `StationPicker` bound to `/selectedStationIds`, defaulted to the leading "
            "candidate",
            acquire,
        )
        self.assertIn("dispatches `earthscope.stations.selected` with the confirmed", acquire)
        self.assertIn('ask_user(..., surface_id="earthscope-stations")', acquire)
        self.assertIn("The surface is the question", acquire)
        self.assertIn(
            "reaches you either as a new turn, if you end this turn here, or as the "
            "answer to a paused question",
            acquire,
        )
        self.assertIn(
            "Pause with `ask_user` when the user asked you to check with them, or "
            "when you still have more to do in this same turn once you know their "
            "choice",
            acquire,
        )
        self.assertIn(
            "End the turn with the surface ready when presenting the candidates is "
            "the natural end of what was asked",
            acquire,
        )
        self.assertIn(
            "never search for or stage a station series before that structured "
            "selection arrives",
            acquire,
        )
        self.assertIn(
            "every rendered or staged station id must come from the tool-returned "
            "ranked points, never invented",
            acquire,
        )
        self.assertNotIn("ChoicePicker", acquire)
        self.assertNotIn("agent.submit", acquire)
        self.assertNotIn("selected_station_ids`", acquire)
        self.assertIn("Do not wait until the end of the turn", acquire)

    def test_root_contract_routes_station_views_to_the_pack_catalog_skill(self) -> None:
        expert = _prose("experts/main.md")

        self.assertIn(
            "load the catalog skill `a2ui-catalog-earthscope-stations`", expert
        )
        self.assertIn(
            "it carries this pack's own `StationMap`/`StationPicker` recipe and the "
            "`earthscope.stations.selected` event contract",
            expert,
        )
        self.assertIn("For every other interactive view, load `present-interactive-analysis`", expert)

    def test_manifest_and_expert_declare_the_earthscope_stations_catalog(self) -> None:
        manifest = _read("AGENT.md")
        expert = _read("experts/main.md")

        self.assertIn(
            "a2ui_catalogs:\n  - clio-workspace\n"
            "  - earthscope-stations: catalogs/earthscope-stations\n",
            manifest,
        )
        self.assertIn("a2ui_catalogs:\n  - clio-workspace\n  - earthscope-stations\n", expert)

    def test_station_catalog_instructions_name_its_catalog_id_for_the_producer(self) -> None:
        """clio-workspace is the default catalog, so a station surface names its own."""

        instructions = _prose("catalogs/earthscope-stations/instructions.md")
        self.assertIn(
            "pass that id as `create_a2ui_surface`'s `catalog_id`", instructions
        )
        self.assertIn("`https://iowarp.ai/a2ui/catalogs/earthscope-stations/v1`", instructions)

    def test_manifest_declares_a_clio_agent_floor(self) -> None:
        """Dependency-free: only that the key exists. The PEP 440 parse/semantics
        assertion lives in earthscope-single-agent/tests/test_a2ui_catalog_pack.py,
        where clio-agent (and the ``packaging`` it brings) is actually available --
        this repo's own top-level ``tests/`` runs under a bare, dependency-free
        interpreter in CI (see .github/workflows/ci.yml's model-inheritance job)."""

        manifest = parse_frontmatter(ROOT / "AGENT.md")

        requires = manifest.get("requires")
        self.assertIsInstance(requires, dict)
        floor = requires.get("clio_agent")
        self.assertIsInstance(floor, str)
        self.assertTrue(floor.strip())

    def test_station_catalog_filter_pins_one_observed_latitude_column(self) -> None:
        acquire = _prose("skills/acquire-earthscope-gnss/SKILL.md")

        self.assertIn('"operator": "between", "value": [-90, 90]', acquire)
        self.assertIn("every filter-condition key must be an observed column name", acquire)
        self.assertIn("Do not split the bounds across invented column aliases", acquire)

    def test_interactive_time_series_is_primary_and_png_is_not_embedded(self) -> None:
        visualize = _prose("skills/visualize-earthscope-gnss/SKILL.md")

        self.assertIn("The primary plot is a live, data-backed A2UI chart", visualize)
        self.assertIn("using exactly one primary `clio.time-series.v1`", visualize)
        self.assertIn("Generate a static PNG only when the user explicitly asks", visualize)
        self.assertIn(
            "Never place the static image below, beside, or inside the interactive chart",
            visualize,
        )

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
        self.assertIn("Collect every returned task id before comparing", compare)
        self.assertNotIn("Never delegate all regions", compare)
        self.assertIn("resolve directly any region you do not delegate", compare)
        self.assertIn("literal cleaned catalog path", compare)
        self.assertIn("Call `pandas_filter_data`", compare)
        self.assertIn("Never substitute the raw staged path", compare)
        self.assertIn("never treat profiling the raw file as normalization", compare)
        self.assertIn("effect: spawn_subagent_with_skill", delegate)
        self.assertIn("You are already running this skill", delegate)
        self.assertIn("Do not call `load_skill`, `spawn_skill_task`", delegate)


if __name__ == "__main__":
    unittest.main()
