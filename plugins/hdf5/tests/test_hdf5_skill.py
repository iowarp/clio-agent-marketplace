"""Contract tests for the hdf5 plugin: the clio-kit server, its tool names, and the skill.

Ported from the retired data-semantics HDF5 subagent tests: the guidance that
subagent carried (bounded reads, close_file, failure reporting, clio-core ingest)
now lives in the hdf5 skill that every HDF5-capable agent loads.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "hdf5"
GUIDE = re.compile(r"`references/([a-z0-9_]+\.md)`")

#: clio-kit hdf5 server tools the skill relies on (unprefixed MCP names).
EXPECTED_HDF5_TOOLS = {
    "analyze_dataset_structure",
    "close_file",
    "export_dataset",
    "get_by_path",
    "get_chunks",
    "get_dtype",
    "get_shape",
    "get_size",
    "identify_io_bottlenecks",
    "list_attributes",
    "list_available_hdf5_files",
    "list_keys",
    "open_file",
    "optimize_access_pattern",
    "read_attribute",
    "read_full_dataset",
    "read_partial_dataset",
    "visit",
}

#: Tools of the retired in-process server; naming them sends the model to a dead tool.
RETIRED_IN_PROCESS_TOOLS = {
    "analyze_file",
    "apply_filter",
    "check_cf_compliance",
    "consult_skill",
    "get_object_metadata",
    "rechunk_dataset",
    "visualize_dataset",
    "list_datasets",
    "analyze_dataset",
}


def _skill_text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def _tools_section() -> str:
    text = _skill_text()
    return text[text.index("## With the hdf5 tools") : text.index("## Which guide")]


def test_the_server_is_clio_kits_hdf5() -> None:
    server = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
    assert server["mcpServers"]["hdf5"]["command"] == "clio-kit"
    assert server["mcpServers"]["hdf5"]["args"] == ["mcp-server", "hdf5"]


def test_the_skill_names_the_current_tool_contract() -> None:
    named = set(re.findall(r"`([a-z_0-9]+)`", _tools_section()))
    assert EXPECTED_HDF5_TOOLS <= named
    assert named.isdisjoint(RETIRED_IN_PROCESS_TOOLS)
    assert named.isdisjoint({f"hdf5_{name}" for name in RETIRED_IN_PROCESS_TOOLS})


def test_the_skill_requires_bounded_evidence_and_descriptive_failures() -> None:
    section = " ".join(_tools_section().split())
    assert "Always call `close_file`" in section
    assert "including after a failed call" in section
    assert "never invent file facts" in section
    assert "name the failed operation" in section
    assert "give a concrete recovery step" in section
    assert "recommendations, not a benchmark" in section
    assert "rather than choosing silently" in section
    assert "references/clio_core_ingest.md" in section


def test_the_router_names_exactly_the_shipped_guides() -> None:
    """Every guide the router names exists, every guide is named, and guides only
    point at each other by file, never at retired per-topic skill ids."""

    shipped = {path.name for path in (SKILL / "references").glob("*.md")}
    assert set(GUIDE.findall(_skill_text())) == shipped
    for guide in (SKILL / "references").glob("*.md"):
        text = guide.read_text(encoding="utf-8")
        assert set(GUIDE.findall(text)) <= shipped, guide.name
        assert not re.findall(r"`hdf5[-_][a-z0-9_-]+`", text), guide.name


def test_the_plugin_ships_one_skill() -> None:
    assert [p.parent.name for p in sorted((PLUGIN / "skills").glob("*/SKILL.md"))] == ["hdf5"]
