"""Spotter Agent Blueprint launch contract."""

from pathlib import Path

import yaml


def test_pack_launches_prepared_environment_without_mutating_it() -> None:
    """A sandboxed CLIO child must not ask uv to rewrite Spotter's environment."""
    manifest = Path(__file__).parents[2] / "AGENT.md"
    frontmatter = manifest.read_text(encoding="utf-8").split("---", 2)[1]
    document = yaml.safe_load(frontmatter)

    args = document["mcp_servers"]["spotter"]["args"]

    assert args[:4] == ["run", "--project", "${SPOTTER_IMPL_DIR}", "--no-sync"]


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
