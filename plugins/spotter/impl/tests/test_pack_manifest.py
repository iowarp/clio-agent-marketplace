"""Spotter plugin launch contract."""

import json
from pathlib import Path

PLUGIN = Path(__file__).parents[2]


def test_plugin_launcher_needs_no_deployment_variables() -> None:
    """Every launcher input is clio-supplied, so a normal install arms with none set."""
    document = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))

    spec = document["mcpServers"]["spotter"]

    assert spec["type"] == "stdio"
    assert spec["command"] == "uv"
    assert spec["args"] == [
        "run",
        "--project",
        "${PLUGIN_ROOT}/impl",
        "spotter-mcp",
        "--clio-config",
        "${CLIO_PROVENANCE_CONFIG}",
    ]


def test_watcher_guidance_names_only_tools_that_exist() -> None:
    """The mission and skills cover provenance, attention and alerting with real tool names."""
    texts = [(PLUGIN / "ai.iowarp.clio" / "prompt" / "mission.md").read_text(encoding="utf-8")]
    texts += [
        path.read_text(encoding="utf-8") for path in sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    ]
    guidance = "\n".join(texts)

    for tool in (
        "spotter_capabilities",
        "spotter_query_tasks",
        "spotter_get_timeline",
        "spotter_get_artifact_lineage",
        "spotter_trace_correlation",
        "spotter_list_attention_calls",
        "spotter_inspect_attention",
        "raise_alert_card",
    ):
        assert f"`{tool}`" in guidance, tool
    for skill in ("investigate-provenance", "inspect-attention", "contain-anomaly"):
        assert f"`{skill}`" in texts[0], skill
        assert (PLUGIN / "skills" / skill / "SKILL.md").is_file(), skill
    for removed in (
        "spotter_campaign_health",
        "spotter_raise_alert",
        "spotter_lift_quarantine",
        "phenotype",
    ):
        assert removed not in guidance, removed


async def test_every_spotter_tool_named_in_the_guidance_is_served(tmp_path: Path) -> None:
    """A `spotter_<tool>` named in the guidance is a tool the MCP actually serves."""
    import re

    from fastmcp import Client

    from spotter_ai.config import NativeQueryConfig
    from spotter_ai.providers.jsonl import JsonlProvider
    from spotter_ai.server import create_server
    from spotter_ai.service import ProvenanceService

    guidance = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            PLUGIN / "ai.iowarp.clio" / "prompt" / "mission.md",
            *sorted((PLUGIN / "skills").glob("*/SKILL.md")),
        ]
    )
    named = set(re.findall(r"`spotter_([a-z_]+)`", guidance))
    provider = JsonlProvider(NativeQueryConfig(tmp_path / "events.jsonl", tmp_path))
    async with Client(create_server(service=ProvenanceService(provider, provider))) as client:
        served = {tool.name for tool in await client.list_tools()}

    assert named
    assert named <= served, sorted(named - served)
