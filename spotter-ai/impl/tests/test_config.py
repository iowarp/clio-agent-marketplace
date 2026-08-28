"""Configuration selection tests."""

from pathlib import Path

import pytest

from spotter_ai.config import SpotterConfigurationError, load_config


def test_selects_flowcept_and_cmf_from_clio_config(tmp_path: Path) -> None:
    """The CLIO config is the only provider and endpoint selection input."""
    flowcept = tmp_path / "flowcept.yaml"
    flowcept.write_text(
        """
project:
  name: clio-live
databases:
  mongodb:
    enabled: true
    uri: mongodb://127.0.0.1:27017
    db: flowcept
""",
        encoding="utf-8",
    )
    config = tmp_path / "clio.yaml"
    config.write_text(
        f"""
provenance:
  agentic:
    providers: [flowcept]
    query_default: flowcept
    flowcept:
      settings_path: {flowcept.name}
  artifacts:
    provider: cmf
    cmf:
      server_url: http://127.0.0.1:8380
      pipeline_name: live-run
""",
        encoding="utf-8",
    )

    result = load_config(config)

    assert result.agentic_provider == "flowcept"
    assert result.artifact_provider == "cmf"
    assert result.flowcept is not None
    assert result.flowcept.database == "flowcept"
    assert result.cmf is not None
    assert result.cmf.server_url == "http://127.0.0.1:8380"
    assert result.native is None


def test_rejects_query_provider_that_clio_did_not_enable(tmp_path: Path) -> None:
    """Spotter never invents a fallback provider."""
    config = tmp_path / "clio.yaml"
    config.write_text(
        """
provenance:
  agentic:
    providers: [jsonl]
    query_default: flowcept
""",
        encoding="utf-8",
    )

    with pytest.raises(SpotterConfigurationError, match="is not enabled"):
        load_config(config)


def test_native_requires_explicit_jsonl_location(tmp_path: Path) -> None:
    """Native querying cannot guess which runtime journal belongs to CLIO."""
    config = tmp_path / "clio.yaml"
    config.write_text("provenance: {}\n", encoding="utf-8")

    with pytest.raises(SpotterConfigurationError, match="explicit.*jsonl.path"):
        load_config(config)
