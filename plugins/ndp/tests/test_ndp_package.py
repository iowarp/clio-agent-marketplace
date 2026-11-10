"""Package contract for ndp: built-in tools first, the MCP server only as a run_code extra."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "work-with-ndp" / "SKILL.md"
MCP_TOOLS = ("search_datasets", "list_organizations", "get_dataset_details", "stage_resource")


def test_the_mcp_server_is_code_only_and_connected_data_is_required() -> None:
    clio = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["extensions"][
        "ai.iowarp.clio"
    ]
    assert clio["requires"] == ["connected-data"]
    assert clio["servers"]["ndp"]["callers"] == "code"
    assert "ndp" in json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]


def test_discovery_is_claimed_directly_and_endpoint_tools_are_deferred() -> None:
    claims = dict(
        re.findall(
            r'native_tool\(\s*"(\w+)"(, defer=True)?\s*\)',
            (PLUGIN / "ai.iowarp.clio" / "tools" / "builtin.py").read_text(encoding="utf-8"),
        )
    )
    assert claims == {
        "connected_data_search_ndp": "",
        "connected_data_ndp_organizations": "",
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
    optional, _, rest = text.partition("## Optional: the ndp MCP server")[2].partition("\n## ")
    assert optional, "the optional MCP section is missing"
    outside = text.replace(optional, "")
    for tool in MCP_TOOLS:
        assert f"ndp_{tool}" not in outside
        assert f"tools.ndp.{tool}" in optional
