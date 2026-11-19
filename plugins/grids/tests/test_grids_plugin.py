"""The grids plugin runs clio-kit's grids server and its skill names only its tools."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
TOOLS = {"grid_open", "grid_edit", "grid_replay"}


class GridsPluginTests(unittest.TestCase):
    def test_it_runs_the_clio_kit_server(self) -> None:
        servers = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(servers["grids"]["args"], ["mcp-server", "grids"])

    def test_the_skill_names_only_server_tools(self) -> None:
        text = (PLUGIN / "skills" / "edit-model-grid" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"`(grid_[a-z_]+)`", text)), TOOLS)


if __name__ == "__main__":
    unittest.main()
