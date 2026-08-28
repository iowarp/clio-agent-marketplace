"""Read-only CLIO and canonical Spotter JSONL provenance queries."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from spotter_ai.config import NativeQueryConfig
from spotter_ai.errors import ProvenanceError, capability_unavailable

_BASE_CAPABILITIES = {
    "list_campaigns",
    "list_workflows",
    "list_agents",
    "query_tasks",
    "summarize_tasks",
    "get_timeline",
    "list_executions",
    "list_artifact_types",
    "list_artifacts",
    "get_execution_lineage",
    "get_artifact_lineage",
    "trace_correlation",
}


class JsonlProvider:
    """Query CLIO semantic events or the documented Spotter JSONL record dialect."""

    name = "native"

    def __init__(self, config: NativeQueryConfig) -> None:
        self._path = config.jsonl_path
        self._workspace_root = config.workspace_root

    def capabilities(self) -> set[str]:
        """Return operations supported by the records currently present."""
        capabilities = set(_BASE_CAPABILITIES)
        records = self._records()
        types = {str(record.get("record_type") or "") for record in records}
        if "pipeline" in types:
            capabilities.add("list_pipelines")
        if "model_card" in types:
            capabilities.add("get_model_card")
        return capabilities

    def health(self) -> dict[str, Any]:
        """Report whether the configured file or directory is readable."""
        paths = self._paths()
        return {
            "provider": self.name,
            "status": "ready" if paths else "unavailable",
            "path": str(self._path),
            "files": len(paths),
        }

    def _paths(self) -> list[Path]:
        if self._path.is_file():
            return [self._path]
        if not self._path.is_dir():
            return []
        return sorted(path for path in self._path.rglob("*.jsonl") if path.is_file())[:1000]

    def _records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in self._paths():
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                raise ProvenanceError(
                    "provider_unavailable",
                    f"could not read native provenance file: {path}",
                    {"reason": type(exc).__name__},
                ) from exc
            for line_number, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ProvenanceError(
                        "invalid_query",
                        f"invalid JSONL record at {path}:{line_number}",
                    ) from exc
                if not isinstance(record, dict):
                    raise ProvenanceError(
                        "invalid_query",
                        f"JSONL record is not an object at {path}:{line_number}",
                    )
                if (
                    not record.get("event_type")
                    and record.get("schema_version") != "spotter.provenance.v1"
                ):
                    raise ProvenanceError(
                        "invalid_query",
                        f"unknown provenance JSONL dialect at {path}:{line_number}",
                    )
                records.append(record)
        return records

    def list_campaigns(self, campaign_id: str | None, limit: int) -> dict[str, Any]:
        """Derive campaigns from canonical records or CLIO trace/workspace identifiers."""
        workflows = self.list_workflows(campaign_id, None, 10_000)["items"]
        counts = Counter(str(row.get("campaign_id") or "") for row in workflows)
        items = [
            {"campaign_id": key, "workflow_count": value}
            for key, value in sorted(counts.items())
            if key and (campaign_id is None or key == campaign_id)
        ][: _limit(limit)]
        return {"items": items, "count": len(items)}

    def list_workflows(
        self, campaign_id: str | None, status: str | None, limit: int
    ) -> dict[str, Any]:
        """List canonical workflows or derive one workflow per CLIO session."""
        records = self._records()
        items: list[dict[str, Any]] = []
        by_session: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            if record.get("record_type") == "workflow":
                item = dict(record.get("data") or {})
                item.setdefault("workflow_id", record.get("workflow_id"))
                item["extensions"] = {"jsonl": record}
                items.append(item)
            elif record.get("event_type"):
                session_id = str(record.get("session_id") or "")
                if session_id:
                    by_session.setdefault(session_id, []).append(record)
        for session_id, events in by_session.items():
            ordered = sorted(events, key=_timestamp)
            terminal = ordered[-1]
            campaign = str(terminal.get("trace_id") or terminal.get("workspace_id") or "")
            items.append(
                {
                    "workflow_id": session_id,
                    "campaign_id": campaign,
                    "name": f"CLIO session {session_id}",
                    "status": str(terminal.get("status") or ""),
                    "started_at": _timestamp(ordered[0]),
                    "ended_at": _timestamp(terminal),
                    "extensions": {"clio": {"event_count": len(events)}},
                }
            )
        items = [
            row
            for row in items
            if (campaign_id is None or row.get("campaign_id") == campaign_id)
            and (status is None or row.get("status") == status)
        ][: _limit(limit)]
        return {"items": items, "count": len(items)}

    def list_agents(self, workflow_id: str | None, limit: int) -> dict[str, Any]:
        """List agents observed in native records."""
        agents: dict[str, dict[str, Any]] = {}
        for record in self._records():
            if workflow_id and _workflow_id(record) != workflow_id:
                continue
            if record.get("record_type") == "agent":
                item = dict(record.get("data") or {})
                agent_id = str(item.get("agent_id") or record.get("agent_id") or "")
            else:
                actor = record.get("actor")
                actor = actor if isinstance(actor, dict) else {}
                agent_id = str(actor.get("agent_id") or "")
                item = {"agent_id": agent_id, "name": agent_id}
            if agent_id:
                agents[agent_id] = item
        items = list(agents.values())[: _limit(limit)]
        return {"items": items, "count": len(items)}

    def query_tasks(
        self,
        *,
        workflow_id: str | None,
        task_id: str | None,
        agent_id: str | None,
        status: str | None,
        activity_id: str | None,
        subtype: str | None,
        limit: int,
    ) -> dict[str, Any]:
        """Query canonical tasks or project CLIO semantic events into tasks."""
        items: list[dict[str, Any]] = []
        for record in self._records():
            item = _task(record)
            if item is None:
                continue
            if workflow_id and item["workflow_id"] != workflow_id:
                continue
            if task_id and item["task_id"] != task_id:
                continue
            if agent_id and item["agent_id"] != agent_id:
                continue
            if status and item["status"] != status:
                continue
            if activity_id and item["activity_id"] != activity_id:
                continue
            if subtype and item["subtype"] != subtype:
                continue
            items.append(item)
        items.sort(key=lambda item: float(item.get("started_at") or 0))
        items = items[: _limit(limit)]
        return {"items": items, "count": len(items)}

    def summarize_tasks(self, workflow_id: str | None) -> dict[str, Any]:
        """Summarize native task status and activity counts."""
        items = self.query_tasks(
            workflow_id=workflow_id,
            task_id=None,
            agent_id=None,
            status=None,
            activity_id=None,
            subtype=None,
            limit=10_000,
        )["items"]
        return {
            "workflow_id": workflow_id,
            "task_count": len(items),
            "status_counts": dict(sorted(Counter(row["status"] for row in items).items())),
            "activity_counts": dict(sorted(Counter(row["activity_id"] for row in items).items())),
        }

    def timeline(self, workflow_id: str, limit: int) -> dict[str, Any]:
        """Build execution spans/nodes/edges from native task evidence."""
        spans = self.query_tasks(
            workflow_id=workflow_id,
            task_id=None,
            agent_id=None,
            status=None,
            activity_id=None,
            subtype=None,
            limit=limit,
        )["items"]
        ids = {str(row["task_id"]) for row in spans}
        nodes = [
            {
                "id": row["task_id"],
                "kind": row["subtype"],
                "label": row["activity_id"],
                "status": row["status"],
                "agent_id": row["agent_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
            }
            for row in spans
        ]
        edges = [
            {"source": row["parent_task_id"], "target": row["task_id"], "kind": "parent"}
            for row in spans
            if row.get("parent_task_id") in ids
        ]
        return {
            "workflow_id": workflow_id,
            "spans": spans,
            "nodes": nodes,
            "edges": edges,
            "complete": len(spans) < _limit(limit),
            "truncated": len(spans) >= _limit(limit),
        }

    def list_pipelines(self, limit: int) -> dict[str, Any]:
        """List canonical pipeline records when the JSONL dialect provides them."""
        records = [
            dict(record.get("data") or {})
            for record in self._records()
            if record.get("record_type") == "pipeline"
        ][: _limit(limit)]
        if not records:
            raise capability_unavailable("list_pipelines", self.name)
        return {"items": records, "count": len(records)}

    def list_executions(
        self, pipeline: str | None, stage: str | None, limit: int
    ) -> dict[str, Any]:
        """List native transform executions or canonical execution records."""
        items: list[dict[str, Any]] = []
        for record in self._records():
            if record.get("record_type") == "execution":
                item = dict(record.get("data") or {})
            elif record.get("event_type") == "artifact.transform.recorded":
                payload = _payload(record)
                item = {
                    "execution_id": str(payload.get("call_id") or record.get("span_id") or ""),
                    "pipeline": str(record.get("workspace_id") or ""),
                    "stage": str((_mapping(payload.get("instrument"))).get("tool") or ""),
                    "status": str(payload.get("status") or record.get("status") or ""),
                    "extensions": {"clio": record},
                }
            else:
                continue
            if pipeline and item.get("pipeline") != pipeline:
                continue
            if stage and item.get("stage") != stage:
                continue
            items.append(item)
        items = items[: _limit(limit)]
        return {"items": items, "count": len(items)}

    def list_artifact_types(self, pipeline: str | None, stage: str | None) -> dict[str, Any]:
        """List artifact kinds recorded in native provenance."""
        del stage
        kinds = {
            str(item.get("artifact_type") or item.get("kind") or "other")
            for item in self.list_artifacts(
                pipeline=pipeline, stage=None, artifact_type=None, limit=10_000
            )["items"]
        }
        items = [{"artifact_type": value} for value in sorted(kinds)]
        return {"items": items, "count": len(items)}

    def list_artifacts(
        self,
        *,
        pipeline: str | None,
        stage: str | None,
        artifact_type: str | None,
        limit: int,
    ) -> dict[str, Any]:
        """List artifacts from CLIO artifact events or canonical JSONL records."""
        del stage
        items: dict[str, dict[str, Any]] = {}
        for record in self._records():
            if record.get("record_type") == "artifact":
                item = dict(record.get("data") or {})
                item.setdefault("artifact_id", record.get("artifact_id"))
                item["extensions"] = {"jsonl": record}
            elif record.get("event_type") in {"artifact.created", "artifact.version.added"}:
                payload = _payload(record)
                item = {
                    "artifact_id": str(payload.get("artifact_id") or ""),
                    "pipeline": str(
                        record.get("workspace_id") or payload.get("workspace_id") or ""
                    ),
                    "artifact_type": str(payload.get("kind") or "other"),
                    "name": str(payload.get("name") or ""),
                    "sha256": str(payload.get("sha256") or ""),
                    "path": str(payload.get("path") or ""),
                    "extensions": {"clio": record},
                }
            else:
                continue
            artifact_id = str(item.get("artifact_id") or "")
            if not artifact_id:
                continue
            if pipeline and item.get("pipeline") != pipeline:
                continue
            if artifact_type and item.get("artifact_type") != artifact_type:
                continue
            items[artifact_id] = item
        result = list(items.values())[: _limit(limit)]
        return {"items": result, "count": len(result)}

    def execution_lineage(self, pipeline: str | None, execution_id: str) -> dict[str, Any]:
        """Return the native artifact graph rooted at one transform execution."""
        graph = self._artifact_graph(pipeline)
        root = f"activity:{execution_id}"
        if not any(node["id"] == root for node in graph["nodes"]):
            raise ProvenanceError("not_found", f"native execution not found: {execution_id}")
        return {"root": root, **graph}

    def artifact_lineage(self, pipeline: str | None, artifact_id: str) -> dict[str, Any]:
        """Return the native artifact/transform graph rooted at one artifact."""
        graph = self._artifact_graph(pipeline)
        if not any(node["id"] == artifact_id for node in graph["nodes"]):
            raise ProvenanceError("not_found", f"native artifact not found: {artifact_id}")
        return {"root": artifact_id, **graph}

    def _artifact_graph(self, pipeline: str | None) -> dict[str, Any]:
        artifacts = self.list_artifacts(
            pipeline=pipeline, stage=None, artifact_type=None, limit=10_000
        )["items"]
        nodes = [
            {"id": row["artifact_id"], "type": "artifact", "label": row.get("name", "")}
            for row in artifacts
        ]
        edges: list[dict[str, str]] = []
        for record in self._records():
            if record.get("event_type") != "artifact.transform.recorded":
                continue
            payload = _payload(record)
            if pipeline and str(record.get("workspace_id") or "") != pipeline:
                continue
            call_id = str(payload.get("call_id") or record.get("span_id") or "")
            activity = f"activity:{call_id}"
            nodes.append(
                {
                    "id": activity,
                    "type": "activity",
                    "label": str((_mapping(payload.get("instrument"))).get("tool") or call_id),
                }
            )
            for row in payload.get("used") or []:
                if isinstance(row, dict) and row.get("artifact_id"):
                    edges.append(
                        {"source": str(row["artifact_id"]), "target": activity, "kind": "used"}
                    )
            for row in payload.get("generated") or []:
                if isinstance(row, dict) and row.get("artifact_id"):
                    edges.append(
                        {"source": activity, "target": str(row["artifact_id"]), "kind": "generated"}
                    )
        unique_nodes = {str(node["id"]): node for node in nodes}
        return {
            "nodes": list(unique_nodes.values()),
            "edges": edges,
            "truncated": None,
            "extensions": {"native": {"workspace_root": str(self._workspace_root)}},
        }

    def model_card(self, model_id: str) -> dict[str, Any]:
        """Return a canonical model card only when one was explicitly recorded."""
        for record in self._records():
            if (
                record.get("record_type") == "model_card"
                and str(record.get("model_id") or "") == model_id
            ):
                return dict(record.get("data") or {})
        raise capability_unavailable("get_model_card", self.name)

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]:
        """Find native records containing an exact correlation identifier."""
        matches: list[dict[str, Any]] = []
        for record in self._records():
            candidates = {
                str(record.get("correlation_id") or ""),
                str(record.get("session_id") or ""),
                str(record.get("turn_id") or ""),
                str(record.get("span_id") or ""),
                str(record.get("event_id") or ""),
            }
            payload = _payload(record)
            candidates.update(
                {
                    str(payload.get("call_id") or ""),
                    str(payload.get("correlation_id") or ""),
                    str(payload.get("artifact_id") or ""),
                }
            )
            if correlation_id in candidates:
                matches.append(record)
                if len(matches) >= _limit(limit):
                    break
        return matches

    def close(self) -> None:
        """Native JSONL queries hold no open resources."""


def _task(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("record_type") == "task":
        item = dict(record.get("data") or {})
        item.setdefault("task_id", record.get("task_id"))
        item.setdefault("workflow_id", record.get("workflow_id"))
        item.setdefault("extensions", {"jsonl": record})
        return item
    event_type = str(record.get("event_type") or "")
    if not event_type:
        return None
    actor = _mapping(record.get("actor"))
    occurred = _timestamp(record)
    subtype = "event"
    if event_type.startswith("lm."):
        subtype = "ai_model_invocation"
    elif event_type.startswith(("tool.", "react.step")):
        subtype = "agent_tool"
    elif event_type.startswith("artifact."):
        subtype = "artifact_provenance_summary"
    return {
        "task_id": str(record.get("span_id") or record.get("event_id") or ""),
        "parent_task_id": str(record.get("parent_span_id") or ""),
        "workflow_id": _workflow_id(record),
        "campaign_id": str(record.get("trace_id") or record.get("workspace_id") or ""),
        "agent_id": str(actor.get("agent_id") or ""),
        "source_agent_id": str(_payload(record).get("source_agent_id") or ""),
        "activity_id": event_type,
        "subtype": subtype,
        "status": str(record.get("status") or ""),
        "started_at": occurred,
        "ended_at": occurred,
        "duration_ms": 0.0,
        "correlation_id": str(record.get("correlation_id") or ""),
        "session_id": str(record.get("session_id") or ""),
        "turn_id": str(record.get("turn_id") or ""),
        "extensions": {"clio": record},
    }


def _workflow_id(record: dict[str, Any]) -> str:
    return str(record.get("workflow_id") or record.get("session_id") or "")


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    return _mapping(record.get("payload"))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _timestamp(record: dict[str, Any]) -> float:
    value = record.get("occurred_at") or record.get("started_at") or 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _limit(value: int) -> int:
    return max(1, min(int(value), 10_000))
