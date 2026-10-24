"""The parquet skill names the clio-kit parquet server's real tools and filter ops."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = (PLUGIN / "skills" / "parquet" / "SKILL.md").read_text(encoding="utf-8")

#: clio-kit parquet server 2.2.5 tools (unprefixed MCP names) and filter ops.
TOOLS = {"summarize_tool", "read_slice_tool", "get_column_preview_tool", "aggregate_column_tool"}
OPS = {
    "equal",
    "not_equal",
    "less",
    "less_equal",
    "greater",
    "greater_equal",
    "is_null",
    "is_valid",
    "is_in",
}


def test_the_server_is_clio_kits_parquet() -> None:
    server = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
    assert server["mcpServers"]["parquet"]["args"] == ["mcp-server", "parquet"]


def test_the_skill_names_the_real_tools_and_ops() -> None:
    section = SKILL[SKILL.index("## The parquet tools") :]
    named = set(re.findall(r"`([a-z_]+)`", section))
    assert TOOLS <= named
    assert OPS <= named
    assert not {n for n in named if n.endswith("_tool")} - TOOLS


def test_the_skill_is_level_two() -> None:
    head = SKILL.split("---", 2)[1]
    assert re.findall(r"(?m)^- (level:L[0-3])$", head) == ["level:L2"]
