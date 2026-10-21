"""Native and canonical JSONL provider tests."""

import json
from pathlib import Path

import pytest

from spotter_ai.config import NativeQueryConfig
from spotter_ai.errors import ProvenanceError
from spotter_ai.providers.jsonl import JsonlProvider


def _write(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")


def test_projects_clio_events_to_execution_and_artifact_semantics(tmp_path: Path) -> None:
    """Native support is explicit projection of recorded CLIO evidence."""
    journal = tmp_path / "events.jsonl"
    _write(
        journal,
        [
            {
                "event_type": "artifact.created",
                "event_id": "evt-1",
                "session_id": "session-1",
                "workspace_id": "workspace-1",
                "occurred_at": "2026-08-22T12:00:00Z",
                "actor": {"agent_id": "agent-1"},
                "payload": {
                    "artifact_id": "artifact-1",
                    "kind": "dataset",
                    "name": "input.csv",
                    "sha256": "abc",
                },
            },
            {
                "event_type": "artifact.transform.recorded",
                "event_id": "evt-2",
                "span_id": "call-1",
                "session_id": "session-1",
                "workspace_id": "workspace-1",
                "occurred_at": "2026-08-22T12:00:01Z",
                "actor": {"agent_id": "agent-1"},
                "payload": {
                    "call_id": "call-1",
                    "instrument": {"tool": "clean"},
                    "used": [{"artifact_id": "artifact-1"}],
                    "generated": [{"artifact_id": "artifact-2"}],
                },
            },
            {
                "event_type": "artifact.created",
                "event_id": "evt-3",
                "session_id": "session-1",
                "workspace_id": "workspace-1",
                "occurred_at": "2026-08-22T12:00:02Z",
                "actor": {"agent_id": "agent-1"},
                "payload": {
                    "artifact_id": "artifact-2",
                    "kind": "dataset",
                    "name": "clean.csv",
                },
            },
        ],
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))

    assert provider.list_workflows(None, None, 10)["items"][0]["workflow_id"] == "session-1"
    tasks = provider.query_tasks(
        workflow_id="session-1",
        task_id=None,
        agent_id=None,
        status=None,
        activity_id=None,
        subtype=None,
        limit=10,
    )
    assert tasks["count"] == 3
    lineage = provider.artifact_lineage("workspace-1", "artifact-2")
    assert {edge["kind"] for edge in lineage["edges"]} == {"used", "generated"}
    assert "list_pipelines" not in provider.capabilities()


def test_rejects_unknown_jsonl_dialect(tmp_path: Path) -> None:
    """Arbitrary JSONL is not silently treated as provenance."""
    journal = tmp_path / "events.jsonl"
    _write(journal, [{"message": "ordinary log line"}])
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))

    with pytest.raises(ProvenanceError, match="unknown provenance JSONL dialect"):
        provider.list_workflows(None, None, 10)


def test_canonical_jsonl_exposes_only_recorded_extra_capabilities(tmp_path: Path) -> None:
    """Pipeline and model-card operations appear only when those records exist."""
    journal = tmp_path / "events.jsonl"
    _write(
        journal,
        [
            {
                "schema_version": "spotter.provenance.v1",
                "record_type": "pipeline",
                "data": {"pipeline": "science"},
            },
            {
                "schema_version": "spotter.provenance.v1",
                "record_type": "model_card",
                "model_id": "model-1",
                "data": {"model": {"name": "model-1"}},
            },
        ],
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))

    assert {"list_pipelines", "get_model_card"} <= provider.capabilities()
    assert provider.list_pipelines(10)["items"] == [{"pipeline": "science"}]
    assert provider.model_card("model-1")["model"]["name"] == "model-1"
