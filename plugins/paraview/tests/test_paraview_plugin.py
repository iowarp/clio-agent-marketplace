"""Contract tests for the paraview plugin: it follows its connector and names live tools."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "paraview-scenes" / "SKILL.md"

#: The tools of clio-kit's paraview server 3.0.0 (unprefixed MCP names).
TOOLS = {
    "open_view",
    "create_filter",
    "remove_scene_object",
    "set_representation",
    "set_timestep",
    "set_camera",
    "fit_camera",
    "inspect_selection",
    "measure_field",
    "capture",
    "export_artifact",
    "export_scene",
    "scene_state",
}

#: Tools of the server it replaced; naming them sends the model to a dead tool.
RETIRED = {
    "load_scientific_data",
    "generate_isosurface",
    "take_viewport_screenshot",
    "set_active_source",
    "get_active_source_names_by_type",
    "show_screenshot_preview",
}


class ParaviewPluginTests(unittest.TestCase):
    def test_it_follows_the_connector_and_binds_its_connection(self) -> None:
        data = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        ext = data["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "paraview")
        self.assertEqual(ext["connections"], {"paraview": "paraview"})
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_the_skill_names_only_live_tools(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        named = set(re.findall(r"`([a-z_]+)`", text))
        self.assertLessEqual(TOOLS, named)
        self.assertFalse(named & RETIRED)
        self.assertIn("set_connector_value", text)

    def test_the_skill_carries_no_instance_literals(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for literal in (r"\bares\b", r"node08", r"\b11111\b", r"/home/", r"wavelet"):
            self.assertIsNone(re.search(literal, text), literal)


if __name__ == "__main__":
    unittest.main()
