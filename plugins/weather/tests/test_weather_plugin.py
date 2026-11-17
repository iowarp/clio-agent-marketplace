"""The weather plugin: its server, its own skills naming only real tools, the skew-T
spec, and ECMWF's skills vendored byte for byte."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"
OWN = ("forecast-probabilities", "weather-extremes", "atmospheric-profiles",
       "climate-evaluation", "skew-t-chart")

#: clio-kit weather server 1.0.0's tools.
WEATHER_TOOLS = {
    "era5_fetch", "ensemble_fetch", "exceedance", "threshold_events", "cross_section",
    "soundings", "ai_forecast", "tc_track", "downscale", "detect_blobs", "stitch_blobs",
    "blob_stats", "climate_index", "composite", "evaluate_run", "cmip_change", "score",
    "station_fetch", "station_verify", "ibtracs_fetch", "track_score",
}
#: Columns of the soundings profile table the skew-T spec reads.
SOUNDING_COLUMNS = {"profile", "pressure", "temperature_c", "dewpoint_c",
                    "parcel_temperature_c"}


class WeatherPluginTests(unittest.TestCase):
    def test_it_runs_the_weather_server_and_keeps_the_forecast_claim(self) -> None:
        servers = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(servers["weather"]["args"], ["mcp-server", "weather"])
        builtin = (PLUGIN / "ai.iowarp.clio" / "tools" / "builtin.py").read_text()
        self.assertIn('native_tool("get_weather_forecast")', builtin)

    def test_own_skills_name_only_server_tools(self) -> None:
        for name in OWN:
            text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            named = {n for n in re.findall(r"`([a-z0-9]+(?:_[a-z0-9]+)+)`", text)
                     if not n.endswith(("_c", "_ms")) and n not in SOUNDING_COLUMNS}
            self.assertLessEqual(named, WEATHER_TOOLS, name)

    def test_the_skew_t_spec_reads_the_sounding_columns_from_the_named_source(self) -> None:
        spec = json.loads((SKILLS / "skew-t-chart" / "skew-t.vl.json").read_text())
        self.assertEqual(spec["data"], {"name": "source"})
        text = json.dumps(spec)
        self.assertNotIn('"url"', text)
        for column in SOUNDING_COLUMNS:
            self.assertIn(column, text)
        scale = spec["encoding"]["y"]["scale"]
        self.assertEqual(scale["type"], "log")
        # The first domain value sits at the bottom of a y axis: the surface pressure
        # first puts high pressure at the bottom, as on a printed skew-T. A reverse
        # flag on top of that turns the chart upside down.
        self.assertGreater(scale["domain"][0], scale["domain"][1])
        self.assertNotIn("reverse", scale)

    def test_the_skew_t_spec_passes_the_chart_guard(self) -> None:
        try:
            from clio_schemas.a2ui.chart_spec import check_chart_spec
        except ImportError:
            self.skipTest("clio-schemas is not installed")
        spec = json.loads((SKILLS / "skew-t-chart" / "skew-t.vl.json").read_text())
        self.assertEqual(check_chart_spec(spec), [])

    def test_ecmwf_skills_are_vendored_unchanged(self) -> None:
        lock = json.loads((PLUGIN / "import-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["license"], "Apache-2.0")
        for name, entry in lock["skills"].items():
            folder = SKILLS / name
            present = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}
            self.assertEqual(present, set(entry["files"]), name)
            for rel, digest in entry["files"].items():
                actual = hashlib.sha256((folder / rel).read_bytes()).hexdigest()
                self.assertEqual(actual, digest, f"{name}/{rel}")
            self.assertTrue((folder / entry["license_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
