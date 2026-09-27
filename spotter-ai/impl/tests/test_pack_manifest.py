"""Spotter Agent Blueprint launch contract."""

from pathlib import Path

import yaml


def test_pack_launcher_needs_no_deployment_variables() -> None:
    """Every launcher input is clio-supplied, so a normal install arms with none set."""
    manifest = Path(__file__).parents[2] / "AGENT.md"
    frontmatter = manifest.read_text(encoding="utf-8").split("---", 2)[1]
    document = yaml.safe_load(frontmatter)

    spec = document["mcp_servers"]["spotter"]

    assert spec["command"] == "uv"
    assert spec["args"] == [
        "run",
        "--project",
        "${CLIO_BLUEPRINT_DIR}/impl",
        "spotter-mcp",
        "--clio-config",
        "${CLIO_PROVENANCE_CONFIG}",
    ]


def test_watcher_declares_forensic_and_provider_aware_tools() -> None:
    """The hybrid watcher keeps containment and general provenance capabilities."""
    root = Path(__file__).parents[2]
    watcher = (root / "experts" / "spotter_watcher.md").read_text(encoding="utf-8")
    frontmatter = watcher.split("---", 2)[1]
    tools = set(yaml.safe_load(frontmatter)["tools"])

    assert {
        "spotter_campaign_health",
        "spotter_diff_runs",
        "spotter_trace_lineage",
        "spotter_raise_alert",
        "spotter_lift_quarantine",
        "spotter_capabilities",
        "spotter_get_timeline",
        "spotter_get_artifact_lineage",
    } <= tools
