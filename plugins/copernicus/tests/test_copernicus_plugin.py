"""The copernicus plugin follows its connector and names only copernicus-mcp's tools."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]

#: copernicus-mcp 0.7.2's tools (the cds_* family is listed once a CDS key is set).
OFFERED = {
    "marine_search_datasets", "marine_search_products", "marine_search_groups",
    "marine_describe_dataset", "marine_get_coordinates", "marine_estimate_subset",
    "marine_subset_dataset", "marine_check_status", "marine_cancel_subset",
    "marine_list_files", "marine_get_files",
    "cds_search_datasets", "cds_describe_dataset", "cds_apply_constraints",
    "cds_estimate_request", "cds_submit_request", "cds_check_request_status",
    "cds_download_request_result", "cds_list_licences", "cds_cancel_request",
    "cds_search_groups",
}


class CopernicusPluginTests(unittest.TestCase):
    def test_it_follows_the_connector_and_binds_its_connection(self) -> None:
        data = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        ext = data["extensions"]["ai.iowarp.clio"]
        self.assertEqual(ext["follows"], "copernicus")
        self.assertEqual(ext["connections"], {"copernicus": "copernicus"})
        self.assertFalse((PLUGIN / "mcp.json").exists())

    def test_the_skill_names_only_offered_tools(self) -> None:
        text = (PLUGIN / "skills" / "copernicus-data" / "SKILL.md").read_text(encoding="utf-8")
        named = set(re.findall(r"\b(?:marine|cds)_[a-z_]+\b", text))
        self.assertTrue(named)
        self.assertLessEqual(named, OFFERED)


if __name__ == "__main__":
    unittest.main()
