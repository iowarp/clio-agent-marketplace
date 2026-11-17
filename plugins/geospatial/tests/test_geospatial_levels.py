"""Level contract for the geospatial plugin: skill levels, servers, and no L3 literals."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
EXPECTED_LEVELS = {
    "resolve-region": "L1",
    "get-geospatial-data": "L1",
    "harmonize-layers": "L1",
}
#: Tool names the skills tell the agent to call, as clio exposes them (server prefix).
SERVER_TOOLS = {
    "geoservices": {"describe_geo_service", "fetch_features", "read_raster_window",
                    "read_point_cloud", "search_stac"},
    "geoprocess": {"reproject", "clip_features", "overlay_features", "zonal_statistics",
                   "raster_difference"},
}


def _skills() -> list[Path]:
    return sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))


def test_every_skill_has_its_level_and_name() -> None:
    assert {p.name for p in _skills()} == set(EXPECTED_LEVELS)
    for skill in _skills():
        head = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        assert re.search(rf"(?m)^name: {re.escape(skill.name)}$", head)
        assert re.findall(r"(?m)^- level:(L[0-3])$", head) == [EXPECTED_LEVELS[skill.name]]


def test_the_plugin_carries_both_servers() -> None:
    servers = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(servers) == set(SERVER_TOOLS)
    for name, server in servers.items():
        assert server["args"] == ["mcp-server", name]


def test_skills_name_only_tools_the_servers_have() -> None:
    known = set().union(*SERVER_TOOLS.values())
    text = "\n".join((s / "SKILL.md").read_text(encoding="utf-8") for s in _skills())
    named = set(re.findall(r"`(?:geoservices_|geoprocess_)?([a-z_]+)`", text))
    tool_like = {
        n for n in named if n in known or (n.endswith(("_features", "_window")) and "max_" not in n)
    }
    assert tool_like <= known


def test_no_run_literals() -> None:
    deny = [
        line.strip()
        for line in (PLUGIN / "lint-denylist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for skill in _skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert not [d for d in deny if d in text], skill.name
