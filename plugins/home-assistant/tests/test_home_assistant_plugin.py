"""Contract tests for the home-assistant plugin: it follows its connector, names only the
tools the connector offers, and ships the upstream skill byte for byte."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
OWN = PLUGIN / "skills" / "home-assistant-sensors" / "SKILL.md"
VENDORED = PLUGIN / "skills" / "home-assistant-best-practices"

#: The ha-mcp tools the Home Assistant connector offers (the `tools` of
#: catalogs/connectors/home-assistant.yaml in clio-agent, ha-mcp 9.2.0).
OFFERED = {
    "ha_get_overview",
    "ha_search",
    "ha_get_state",
    "ha_get_history",
    "ha_get_entity",
    "ha_get_device",
    "ha_list_floors_areas",
    "ha_get_zone",
    "ha_list_services",
    "ha_call_service",
    "ha_bulk_control",
    "ha_get_system_health",
    "ha_get_automation_traces",
    "ha_config_get_automation",
    "ha_config_set_automation",
    "ha_config_remove_automation",
    "ha_config_get_script",
    "ha_config_set_script",
    "ha_config_remove_script",
    "ha_config_get_scene",
    "ha_config_set_scene",
    "ha_config_remove_scene",
    "ha_config_list_helpers",
    "ha_config_set_helper",
    "ha_config_get_dashboard",
    "ha_config_set_dashboard",
    "ha_set_entity",
}


class HomeAssistantPluginTests(unittest.TestCase):
    def test_it_follows_the_connector_and_binds_its_connection(self) -> None:
        data = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        ext = data["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "home-assistant")
        self.assertEqual(ext["connections"], {"home-assistant": "home-assistant"})
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_its_own_skill_names_only_offered_tools(self) -> None:
        text = OWN.read_text(encoding="utf-8")
        named = set(re.findall(r"\bha_[a-z_]+\b", text))
        # A family named by its prefix (ha_config_get_*) is fine; every full name is offered.
        named = {name for name in named if not name.endswith("_")}
        self.assertTrue(named)
        self.assertLessEqual(named, OFFERED)
        self.assertIn("home-assistant-best-practices", text)

    def test_the_vendored_skill_matches_its_lock(self) -> None:
        lock = json.loads((PLUGIN / "import-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["repository"], "https://github.com/homeassistant-ai/skills")
        self.assertRegex(lock["revision"], r"^[0-9a-f]{40}$")
        self.assertEqual(lock["license"], "MIT")
        present = {
            path.relative_to(VENDORED).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(VENDORED.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(present, lock["files"])
        self.assertIn("MIT License", (VENDORED / lock["license_file"]).read_text(encoding="utf-8"))

    def test_no_instance_literals(self) -> None:
        text = OWN.read_text(encoding="utf-8")
        for literal in (r"qc-h\.net", r"\b\w+\.local:\d+", r"eyJ[A-Za-z0-9_-]{10,}"):
            self.assertIsNone(re.search(literal, text), literal)


if __name__ == "__main__":
    unittest.main()
