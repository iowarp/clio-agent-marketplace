"""Contract tests for the ibm-quantum plugin: it follows its connector and names live tools."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"

#: The tools of the fork's ibm-quantum-mcp-server (unprefixed MCP names).
TOOLS = {
    "run_sampler", "run_estimator", "get_job_status", "get_job_results", "list_my_jobs",
    "cancel_job", "compare_jobs", "record_job", "usage_info", "list_backends",
    "least_busy_backend", "get_backend_properties", "get_backend_calibration",
    "find_optimal_qubit_chains", "find_optimal_qv_qubits", "get_coupling_map",
    "transpile_circuit", "compare_optimization_levels", "analyze_circuit",
    "convert_qpy_to_qasm3", "convert_qasm3_to_qpy", "load_circuit_from_qasm",
    "export_circuit_to_qasm", "active_account_info", "active_instance_info",
    "available_instances", "search_docs", "get_page", "lookup_error_code",
    "view_circuit", "view_layout", "view_results", "view_backend",
}
#: Names of the servers it replaced or that the connector does not serve.
RETIRED = {
    "run_sampler_tool", "run_estimator_tool", "setup_ibm_quantum_account",
    "setup_ibm_quantum_account_tool", "ai_routing", "hybrid_ai_transpile",
}
#: CLIO tools and the view's app tools the skills may name.
OTHERS = {"offer_plugin", "create_a2ui_surface", "capture_a2ui_surface", "run_code", "load_skill",
          "focus", "show_jobs"}


def _skill_texts() -> dict[str, str]:
    return {p.parent.name: p.read_text(encoding="utf-8") for p in SKILLS.glob("*/SKILL.md")}


class IbmQuantumPluginTests(unittest.TestCase):
    def test_it_follows_the_connector_and_binds_its_connection(self) -> None:
        data = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        ext = data["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "ibm-quantum")
        self.assertEqual(ext["connections"], {"ibm-quantum": "ibm-quantum"})
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_the_skills_name_only_live_tools(self) -> None:
        named: set[str] = set()
        for text in _skill_texts().values():
            named |= {n for n in re.findall(r"`([a-z_]+)`", text) if "_" in n}
        self.assertFalse(named & RETIRED)
        self.assertLessEqual(
            {"run_sampler", "run_estimator", "compare_jobs", "view_circuit", "view_layout",
             "view_results", "usage_info", "record_job"},
            named,
        )
        unknown = {n for n in named if n.endswith(("_circuit", "_jobs", "_results", "_info"))}
        self.assertLessEqual(unknown, TOOLS | OTHERS)

    def test_the_skills_carry_no_account_or_job_literals(self) -> None:
        for name, text in _skill_texts().items():
            with self.subTest(skill=name):
                self.assertIsNone(re.search(r"crn:v1:[a-z]", text))
                self.assertIsNone(re.search(r"local-[0-9a-f]{6,}", text))
                self.assertIsNone(re.search(r"\b\d{1,3}(\.\d+)?\s?%", text))

    def test_the_workbench_links_the_circuit_and_layout_views(self) -> None:
        surface = json.loads(
            (SKILLS / "quantum-workbench" / "references" / "quantum-workbench.json").read_text()
        )
        apps = {c["id"]: c for c in surface["components"] if c["component"] == "clio.mcp-app.v1"}
        self.assertEqual({a["tool"] for a in apps.values()}, {"view_circuit", "view_layout", "view_results"})
        self.assertTrue(all(a["server"] == "ibm-quantum" for a in apps.values()))
        channel = {"key": "selected_gate", "path": "/quantum/selected_gate", "tool": "focus"}
        self.assertIn(channel, apps["circuit"]["state"])
        self.assertIn(channel, apps["layout"]["state"])


if __name__ == "__main__":
    unittest.main()
