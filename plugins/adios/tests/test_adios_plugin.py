"""Contract tests for the adios plugin: clio-kit's adios server and the adios2 skill."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = (PLUGIN / "skills" / "adios2" / "SKILL.md").read_text(encoding="utf-8")

#: clio-kit adios server 2.2.5 tools (unprefixed MCP names) and their parameters.
TOOLS = {
    "list_bp5": "directory",
    "inspect_variables": "filename, variable_name?",
    "inspect_variables_at_step": "filename, variable_name, step",
    "inspect_attributes": "filename, variable_name?",
    "read_variable_at_step": "filename, variable_name, target_step",
}


def test_the_server_is_clio_kits_adios() -> None:
    server = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
    assert server["mcpServers"]["adios"]["command"] == "clio-kit"
    assert server["mcpServers"]["adios"]["args"] == ["mcp-server", "adios"]


def test_the_skill_names_exactly_the_servers_tools() -> None:
    section = SKILL[SKILL.index("## The adios tools") :]
    calls = dict(re.findall(r"`([a-z_0-9]+)\(([^)]*)\)`", section))
    assert calls == TOOLS


def test_the_skill_states_its_contract_and_level() -> None:
    head = SKILL.split("---", 2)[1]
    assert re.findall(r"(?m)^- (level:L[0-3])$", head) == ["level:L2"]
    assert "**BP4 and BP5**" in SKILL
    assert "BP3" in SKILL.split("## Layout")[0]
