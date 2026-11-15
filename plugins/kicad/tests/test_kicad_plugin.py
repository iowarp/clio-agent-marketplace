"""Contract tests for the kicad plugin: it follows its connector, its copies of the
fork's skills match the pin, its skills name live tools, and its workbench links views."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"

#: Server tools of the KiCad connector (kicad-mcp-pro at the pinned commit) the
#: plugin's own skills name.
CLIO_TOOLS = {"view_pdf"}
TOOLS = {
    "export_spice_netlist",
    "export_step",
    "kicad_get_project_info",
    "kicad_session_status",
    "kicad_set_project",
    "lib_bind_part_to_symbol",
    "lib_compare_parts",
    "lib_generate_symbol_from_pintable",
    "lib_get_component_specs",
    "lib_get_datasheet_url",
    "lib_get_footprint_info",
    "lib_search_parametric",
    "pcb_add_mounting_holes",
    "pcb_add_track",
    "pcb_add_tracks_bulk",
    "pcb_add_via",
    "pcb_add_zone",
    "pcb_auto_place_by_schematic",
    "pcb_auto_place_force_directed",
    "pcb_critique_placement",
    "pcb_delete_items",
    "pcb_delete_object",
    "pcb_get_board_summary",
    "pcb_get_design_rules",
    "pcb_get_footprints",
    "pcb_get_layers",
    "pcb_get_net_statistics",
    "pcb_get_nets",
    "pcb_get_ratsnest",
    "pcb_get_stackup",
    "pcb_get_tracks",
    "pcb_get_vias",
    "pcb_get_zones",
    "pcb_import_outline_dxf",
    "pcb_move_footprint",
    "pcb_net_inspector",
    "pcb_place_component",
    "pcb_place_decoupling_caps",
    "pcb_placement_quality_gate",
    "pcb_quality_gate",
    "pcb_refill_zones",
    "pcb_route_corner_style_gate",
    "pcb_save",
    "pcb_score_placement",
    "pcb_set_board_outline",
    "pcb_set_board_outline_shape",
    "pcb_set_design_rules",
    "pcb_set_footprint_layer",
    "pcb_set_footprint_locked",
    "pcb_set_keepout_zone",
    "pcb_set_stackup",
    "pcb_stackup_consistency_gate",
    "pcb_sync_from_schematic",
    "pcb_transfer_quality_gate",
    "pcb_visual_qa",
    "route_autoroute_freerouting",
    "route_from_pad_to_pad",
    "route_set_net_class_rules",
    "route_single_track",
    "run_drc",
    "run_erc",
    "sch_get_pin_positions",
    "view_board",
    "view_bom",
    "view_checks",
    "view_parts",
    "view_schematic",
    "view_stackup",
}

#: The views' own tools (MCP Apps app tools), which a skill may name too.
APP_TOOLS = {"focus", "set_layers", "select_row", "select", "capture", "describe_region"}

#: Skills this plugin adds; the others are copies of the fork's skills.
OWN = {"install-kicad", "pcb-placement", "pcb-routing", "datasheet-pin-check", "pcb-pipeline"}

#: Simulation is the spice connector's; the connector hides these tools.
HIDDEN_PREFIX = "sim_"


class KicadPluginTests(unittest.TestCase):
    def test_it_follows_the_connector_and_needs_documents_and_the_log(self) -> None:
        data = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        ext = data["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "kicad")
        self.assertEqual(ext["connections"], {"kicad": "kicad"})
        self.assertEqual(ext["requires"], ["documents", "science-log"])

    def test_the_fork_skill_copies_match_the_pin(self) -> None:
        pin = json.loads((PLUGIN / "fork-skills.json").read_text(encoding="utf-8"))
        self.assertRegex(pin["commit"], r"^[0-9a-f]{40}$")
        copied = {
            str(path.relative_to(PLUGIN))
            for folder in SKILLS.iterdir()
            if folder.name not in OWN
            for path in folder.rglob("*")
            if path.is_file()
        }
        self.assertEqual(copied, set(pin["files"]))
        for name, digest in pin["files"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest(), digest)

    def test_its_own_skills_name_only_live_tools(self) -> None:
        pattern = re.compile(r"`((?:pcb|lib|route|sch|run|view|export|kicad)_[a-z0-9_]+)`")
        for skill in sorted(OWN):
            with self.subTest(skill=skill):
                text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                # CLIO's own tools that share a prefix with the connector's (view_pdf).
                named = set(pattern.findall(text)) - CLIO_TOOLS
                self.assertLessEqual(named, TOOLS)
                self.assertNotIn(HIDDEN_PREFIX, " ".join(named))

    def test_the_pipeline_asks_for_keys_through_the_card_not_the_chat(self) -> None:
        text = (SKILLS / "pcb-pipeline" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("offer_plugin", text)
        self.assertIn("needs", text)
        self.assertIn("never ask for a key in a message", text)

    def test_the_workbench_links_board_bom_and_checks_by_selection(self) -> None:
        doc = json.loads(
            (SKILLS / "pcb-pipeline" / "references" / "pcb-workbench.json").read_text("utf-8")
        )
        components = {row["id"]: row for row in doc["components"]}
        self.assertEqual(len(components), len(doc["components"]))
        views = {cid: row for cid, row in components.items() if row["component"] == "clio.mcp-app.v1"}
        self.assertEqual({row["tool"] for row in views.values()}, {"view_board", "view_bom", "view_checks"})
        for row in views.values():
            self.assertEqual(row["server"], "kicad")
            paths = {channel["path"] for channel in row["state"]}
            self.assertIn("/pcb/selection", paths)
            for channel in row["state"]:
                self.assertIn(channel.get("tool", "select"), APP_TOOLS)
        self.assertEqual(components["placement"]["component"], "clio.chart.v1")
        for row in components.values():
            for child in row.get("children", []):
                self.assertIn(child, components)


if __name__ == "__main__":
    unittest.main()
