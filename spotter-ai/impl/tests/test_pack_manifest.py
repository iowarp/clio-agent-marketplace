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
