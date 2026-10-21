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


def test_watcher_prompt_keeps_forensic_and_provider_aware_guidance() -> None:
    """The hybrid watcher keeps containment and general provenance capabilities."""
    prompt = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((PLUGIN / "ai.iowarp.clio" / "prompt").glob("*.md"))
    )

    for tool in (
        "spotter_campaign_health",
        "spotter_diff_runs",
        "spotter_trace_lineage",
        "spotter_raise_alert",
        "spotter_lift_quarantine",
        "spotter_capabilities",
        "spotter_trace_correlation",
        "spotter_inspect_attention",
    ):
        assert f"`{tool}`" in prompt, tool
