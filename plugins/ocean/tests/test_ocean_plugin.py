"""The ocean plugin follows its connector, needs grids, and its skills name only real
tools and real columns of the ocean server's tables."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"

#: clio-kit ocean server 1.0.0's tools, and the grids tool the model skill opens.
TOOLS = {
    "ctd_read", "teos10", "water_masses", "argo_fetch", "glider_fetch", "profile_metrics",
    "section", "transport", "overturning", "harmonics", "spectra", "sea_level_decompose",
    "particles", "eddy_track", "track_crossings", "swath_fetch", "swath_compare",
    "mhw_point", "mhw_track", "mhw_events", "bloom_phenology", "mixed_layer_budget",
    "cruise_plan", "drift", "colocate", "mom6_preflight", "grid_open",
    "shell_bash",  # CLIO core
}
COLUMNS = {"SA", "CT", "sigma0", "water_mass", "profile", "pressure", "kind", "label"}


class OceanPluginTests(unittest.TestCase):
    def test_it_follows_its_connector_and_requires_grids(self) -> None:
        ext = json.loads((PLUGIN / "plugin.json").read_text())["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "ocean")
        self.assertEqual(ext["connections"], {"ocean": "ocean"})
        self.assertEqual(ext["requires"], ["grids"])
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_skills_name_only_server_tools(self) -> None:
        for skill in SKILLS.iterdir():
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            named = {n for n in re.findall(r"`([a-z0-9]+_[a-z0-9_]+)`", text)
                     if n not in COLUMNS}
            self.assertLessEqual(named, TOOLS, skill.name)

    def test_the_ts_spec_reads_teos10_columns_from_the_named_source(self) -> None:
        spec = json.loads((SKILLS / "ts-diagram" / "ts-diagram.vl.json").read_text())
        self.assertEqual(spec["data"], {"name": "source"})
        fields = set(re.findall(r'"field": "([A-Za-z_0-9]+)"', json.dumps(spec)))
        self.assertLessEqual(fields, COLUMNS)

    def test_the_ts_spec_passes_the_chart_guard(self) -> None:
        try:
            from clio_schemas.a2ui.chart_spec import check_chart_spec
        except ImportError:
            self.skipTest("clio-schemas is not installed")
        spec = json.loads((SKILLS / "ts-diagram" / "ts-diagram.vl.json").read_text())
        self.assertEqual(check_chart_spec(spec), [])


if __name__ == "__main__":
    unittest.main()
