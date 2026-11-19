"""Package contract for ndp: CLIO's own NDP source, with no MCP server."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "work-with-ndp" / "SKILL.md"
MCP_TOOLS = ("search_datasets", "list_organizations", "get_dataset_details", "stage_resource")


def test_no_mcp_server_and_connected_data_is_required() -> None:
    """NDP goes through CLIO's source semantics only: attached sources, not MCP reads."""
    clio = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["extensions"][
        "ai.iowarp.clio"
    ]
    assert clio["requires"] == ["connected-data", "geospatial"]
    assert "servers" not in clio and not (PLUGIN / "mcp.json").exists()


def test_discovery_is_claimed_directly_and_endpoint_tools_are_deferred() -> None:
    claims = dict(
        re.findall(
            r'native_tool\(\s*"(\w+)"(, defer=(?:True|False))?\s*\)',
            (PLUGIN / "ai.iowarp.clio" / "tools" / "builtin.py").read_text(encoding="utf-8"),
        )
    )
    assert claims == {
        # Listed explicitly: declaring nothing defers a built-in.
        "connected_data_search_ndp": ", defer=False",
        "connected_data_ndp_organizations": ", defer=False",
        "connected_data_ndp_tiles_covering": ", defer=False",
        "connected_data_ndp_endpoint_connect": ", defer=True",
        "connected_data_ndp_endpoint_operations": ", defer=True",
        "connected_data_ndp_upload_artifact": ", defer=True",
        "connected_data_ndp_endpoint_request": ", defer=True",
    }


def test_the_skill_works_without_the_mcp_server() -> None:
    text = SKILL.read_text(encoding="utf-8")
    head = text.split("---", 2)[1]
    assert re.search(r"(?m)^title: Working with NDP$", head)
    assert re.search(r"(?m)^description: Use this skill when working with", head)
    assert "connected_data_search_ndp" in text and "connected_data_ndp_organizations" in text
    # The tools no longer wait for an attached dataset or saved Endpoint.
    assert "next turn" not in text and "activate" not in text
    assert "## Optional: the ndp MCP server" not in text
    for tool in MCP_TOOLS:
        assert f"ndp_{tool}" not in text and f"tools.ndp.{tool}" not in text
    # What only the MCP server used to give is part of the source search now.
    assert "resource_format" in text and "description" in text
    assert "connected_data_connect" in text
