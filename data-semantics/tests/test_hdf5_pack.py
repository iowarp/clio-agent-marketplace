"""Contract tests for the data-semantics HDF5 expert."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

PACK_ROOT = Path(__file__).resolve().parents[1]
HDF5_EXPERT_PATH = PACK_ROOT / "experts" / "hdf5.md"

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


def _document(path: Path) -> tuple[dict[str, Any], str]:
    """Return parsed YAML frontmatter and Markdown body for a pack document."""

    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    frontmatter, separator, body = text[4:].partition("\n---\n")
    assert separator, f"unterminated frontmatter: {path}"
    metadata = yaml.safe_load(frontmatter)
    assert isinstance(metadata, dict), f"frontmatter must be a mapping: {path}"
    return metadata, body.strip()


def test_hdf5_expert_is_registered_and_routable() -> None:
    """The pack and root orchestrator must both expose the HDF5 child."""

    pack, _ = _document(PACK_ROOT / "AGENT.md")
    main, main_prompt = _document(PACK_ROOT / "experts" / "main.md")
    route, route_prompt = _document(PACK_ROOT / "skills" / "route_dataset_questions" / "SKILL.md")

    assert pack["mcp_servers"]["hdf5"] == "clio-kit mcp-server hdf5"
    assert "experts/hdf5.md" in pack["experts"]
    assert "hdf5" in main["children"]
    assert route["name"] == "route_dataset_questions"
    assert "Do not send such a request to `data`" in main_prompt
    assert "Do not route an HDF5 request to the generic `data` expert" in route_prompt


def test_hdf5_expert_uses_current_clio_kit_tool_contract() -> None:
    """The expert must expose the current namespaced MCP tools, not retired tools."""

    expert, prompt = _document(HDF5_EXPERT_PATH)
    tools = set(expert["tools"])

    assert expert["id"] == "hdf5"
    assert expert["parent"] == "main"
    assert expert["module_kind"] == "react"
    assert tools == EXPECTED_HDF5_TOOLS
    assert tools.isdisjoint(RETIRED_IN_PROCESS_TOOLS)
    assert "Always call `close_file`" in prompt
    assert "recommendations, not a\nbenchmark" in prompt


def test_hdf5_guidance_comes_from_the_builtin_skill() -> None:
    """HDF5 guidance ships as clio-agent's built-in `hdf5` skill, not pack copies."""

    expert, prompt = _document(HDF5_EXPERT_PATH)
    skills = {str(skill) for skill in expert["skills"]}
    bundled = {
        path.name
        for path in (PACK_ROOT / "skills").iterdir()
        if path.is_dir() and path.name.startswith("hdf5")
    }

    assert "hdf5" in skills
    assert not {skill for skill in skills if skill.startswith("hdf5_")}
    assert not bundled, "per-topic HDF5 skills moved to clio-agent's built-in `hdf5`"
    assert "references/clio_core_ingest.md" in prompt


def test_pack_documents_do_not_reference_retired_hdf5_skill_ids() -> None:
    """No pack document routes the agent to a retired per-topic HDF5 skill."""

    retired: set[str] = set()
    for path in PACK_ROOT.rglob("*.md"):
        retired.update(re.findall(r"`(hdf5_(?!list|open|close|get|read|visit|analyze|identify|optimize)[a-z0-9_]+)`", path.read_text(encoding="utf-8")))

    assert not retired


def test_hdf5_expert_requires_bounded_evidence_and_descriptive_failures() -> None:
    """The system prompt must require evidence, bounded reads, and recovery guidance."""

    _, prompt = _document(HDF5_EXPERT_PATH)

    assert "sample values with\n`read_partial_dataset` rather than pulling whole datasets" in prompt
    assert "Never invent file facts" in prompt
    assert "name the failed operation" in prompt
    assert "give a concrete recovery step" in prompt
    assert "recommendation as measured performance" in prompt
