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


def _event(session: str, event_id: str, occurred: str, **extra: object) -> dict[str, object]:
    return {
        "event_type": "tool.called",
        "event_id": event_id,
        "session_id": session,
        "occurred_at": occurred,
        "actor": {"agent_id": "agent-1"},
        **extra,
    }


def test_filtered_queries_parse_only_lines_that_can_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The journal is every session ever recorded: a scoped query must not parse it all."""
    journal = tmp_path / "journal"
    journal.mkdir()
    _write(
        journal / "a.jsonl",
        [_event("session-a", f"a-{n}", "2026-08-22T12:00:00Z") for n in range(3)],
    )
    _write(
        journal / "b.jsonl",
        [_event("session-b", f"b-{n}", "2026-08-22T12:00:00Z") for n in range(50)],
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    parsed: list[bytes] = []
    real_loads = json.loads

    def counting_loads(line: bytes) -> object:
        parsed.append(line)
        return real_loads(line)

    monkeypatch.setattr("spotter_ai.providers.jsonl.json.loads", counting_loads)

    summary = provider.summarize_tasks("session-a")

    assert summary["task_count"] == 3
    assert len(parsed) == 3
    parsed.clear()
    assert provider.find_correlation("b-7", 10)[0]["event_id"] == "b-7"
    assert len(parsed) == 1


def test_streamed_aggregates_match_a_stable_sort(tmp_path: Path) -> None:
    """Session spans and task order are what sorting the whole journal by time gave."""
    journal = tmp_path / "events.jsonl"
    _write(
        journal,
        [
            _event("s", "late", "2026-08-22T12:00:05Z", status="first-terminal"),
            _event("s", "early", "2026-08-22T12:00:01Z"),
            _event("s", "tie", "2026-08-22T12:00:05Z", status="last-terminal"),
            _event("s", "middle", "2026-08-22T12:00:03Z"),
        ],
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))

    (workflow,) = provider.list_workflows(None, None, 10)["items"]
    tasks = provider.query_tasks(
        workflow_id="s",
        task_id=None,
        agent_id=None,
        status=None,
        activity_id=None,
        subtype=None,
        limit=3,
    )["items"]

    assert workflow["status"] == "last-terminal"
    assert workflow["ended_at"] - workflow["started_at"] == 4
    assert workflow["extensions"]["clio"]["event_count"] == 4
    assert [task["task_id"] for task in tasks] == ["early", "middle", "late"]


def test_summary_counts_every_task_past_the_listing_limit(tmp_path: Path) -> None:
    """A summary is a count over the journal, not over one listing page."""
    journal = tmp_path / "events.jsonl"
    _write(journal, [_event("s", f"e-{n}", "2026-08-22T12:00:00Z") for n in range(10_050)])
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))

    assert provider.summarize_tasks("s")["task_count"] == 10_050
