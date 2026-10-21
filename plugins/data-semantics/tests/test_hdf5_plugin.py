"""Contract tests for the data-semantics plugin's HDF5 subagent and the HDF5 skill."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from clio_agent.plugins.loader import load_plugin

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGINS = PLUGIN_ROOT.parent

EXPECTED_HDF5_TOOLS = {
    "hdf5_analyze_dataset_structure",
    "hdf5_close_file",
    "hdf5_get_by_path",
    "hdf5_get_chunks",
    "hdf5_get_dtype",
    "hdf5_get_shape",
    "hdf5_get_size",
    "hdf5_identify_io_bottlenecks",
    "hdf5_list_attributes",
    "hdf5_list_available_hdf5_files",
    "hdf5_list_keys",
    "hdf5_open_file",
    "hdf5_optimize_access_pattern",
    "hdf5_read_attribute",
    "hdf5_read_partial_dataset",
    "hdf5_visit",
}

RETIRED_IN_PROCESS_TOOLS = {
    "hdf5_analyze_file",
    "hdf5_apply_filter",
    "hdf5_check_cf_compliance",
    "hdf5_consult_skill",
    "hdf5_get_object_metadata",
    "hdf5_rechunk_dataset",
    "hdf5_visualize_dataset",
}


@pytest.fixture(scope="module")
def record():
    return load_plugin(PLUGIN_ROOT, marketplace="test", trusted=True)


def _subagent(record, subagent_id: str):
    return next(sub for sub in record.subagents if sub.id == subagent_id)


HDF5_SKILL = PLUGINS / "hdf5" / "skills" / "hdf5"
GUIDE = re.compile(r"`references/([a-z0-9_]+\.md)`")


def test_hdf5_subagent_is_defined_and_routable(record) -> None:
    """The plugin defines the HDF5 subagent and the routing guidance points to it."""

    assert not record.errors
    assert {"data", "analysis", "visualization", "hdf5"} <= {sub.id for sub in record.subagents}
    routing = (PLUGIN_ROOT / "ai.iowarp.clio" / "prompt" / "routing.md").read_text(encoding="utf-8")
    route = (PLUGIN_ROOT / "skills" / "route-dataset-questions" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "Do not send such a request to `data`" in routing
    assert "Do not route an HDF5 request to the generic `data` expert" in route
    server = json.loads((PLUGINS / "hdf5" / "mcp.json").read_text(encoding="utf-8"))
    assert server["mcpServers"]["hdf5"]["args"] == ["mcp-server", "hdf5"]


def test_hdf5_subagent_uses_current_clio_kit_tool_contract(record) -> None:
    """The subagent allows the current namespaced MCP tools, not retired tools."""

    hdf5 = _subagent(record, "hdf5")
    tools = set(hdf5.tools or ())

    assert "hdf5" in hdf5.plugins
    assert tools - {"load_skill"} == EXPECTED_HDF5_TOOLS
    assert tools.isdisjoint(RETIRED_IN_PROCESS_TOOLS)
    assert "Always call `close_file`" in hdf5.prompt
    assert "recommendations, not a\nbenchmark" in hdf5.prompt


def test_hdf5_guidance_is_the_hdf5_plugins_single_skill(record) -> None:
    """The HDF5 guidance ships once, in the hdf5 plugin; data-semantics keeps no copy."""

    assert not any(skill.id.startswith("hdf5") for skill in record.skills)
    hdf5 = load_plugin(PLUGINS / "hdf5", marketplace="test", trusted=True)
    assert not hdf5.errors
    assert [skill.id for skill in hdf5.skills] == ["hdf5"]
    assert "references/clio_core_ingest.md" in _subagent(record, "hdf5").prompt


def test_the_router_names_exactly_the_shipped_guides() -> None:
    """Every guide the router names exists, every guide is named, and guides only
    point at each other by file, never at the retired per-topic skill ids."""

    shipped = {path.name for path in (HDF5_SKILL / "references").glob("*.md")}
    router = (HDF5_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert set(GUIDE.findall(router)) == shipped
    for guide in (HDF5_SKILL / "references").glob("*.md"):
        text = guide.read_text(encoding="utf-8")
        assert set(GUIDE.findall(text)) <= shipped, guide.name
        assert not re.findall(r"`hdf5[-_][a-z0-9_-]+`", text), guide.name


def test_hdf5_subagent_requires_bounded_evidence_and_descriptive_failures(record) -> None:
    """The subagent prompt requires evidence, bounded reads, and recovery guidance."""

    prompt = _subagent(record, "hdf5").prompt

    assert "sample values with\n`read_partial_dataset` rather than pulling whole datasets" in prompt
    assert "Never invent file facts" in prompt
    assert "name the failed operation" in prompt
    assert "give a concrete recovery step" in prompt
    assert "recommendation as measured performance" in prompt
