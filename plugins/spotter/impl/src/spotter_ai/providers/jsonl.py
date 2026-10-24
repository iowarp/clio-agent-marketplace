"""Read-only CLIO and canonical Spotter JSONL provenance queries.

The native journal is every session CLIO ever recorded, so it grows without bound
(gigabytes on a long-lived host). Queries stream it one line at a time and keep
only what they return: holding the parsed journal costs several times its size on
disk, and doing that per call took the server down with it. A query that filters
on an identifier skips lines that cannot contain it before parsing them; only the
lines a query parses are validated.
"""

from __future__ import annotations

import heapq
import json
import re
from collections import Counter
from collections.abc import Iterator
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
        extra = {"pipeline": "list_pipelines", "model_card": "get_model_card"}
        for record in self._records(all_of=("record_type",), any_of=tuple(extra)):
            operation = extra.pop(str(record.get("record_type") or ""), None)
            if operation:
                capabilities.add(operation)
            if not extra:
                break
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

    def _records(
        self, *, all_of: tuple[str | None, ...] = (), any_of: tuple[str, ...] = ()
    ) -> Iterator[dict[str, Any]]:
        """Stream records, parsing only lines that hold every ``all_of`` and one ``any_of``.

        Each value is a string some field of a matching record equals; ``None`` (an
        unset filter) is ignored.
        """
        required = [_needle(value) for value in all_of if value]
        required = [needle for needle in required if needle]
        optional = [needle for needle in map(_needle, any_of) if needle]
        if len(optional) < len(any_of):
            optional = []
        for path in self._paths():
            yield from self._file_records(path, required, optional)

    def _file_records(
        self, path: Path, required: list[bytes], optional: list[bytes]
    ) -> Iterator[dict[str, Any]]:
        try:
            handle = path.open("rb")
        except OSError as exc:
            raise ProvenanceError(
                "provider_unavailable",
                f"could not read native provenance file: {path}",
                {"reason": type(exc).__name__},
            ) from exc
        with handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                if any(needle not in line for needle in required):
                    continue
                if optional and not any(needle in line for needle in optional):
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
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
                yield record

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
        items: list[dict[str, Any]] = []
        sessions: dict[str, _SessionSpan] = {}
        for record in self._records():
            if record.get("record_type") == "workflow":
                item = dict(record.get("data") or {})
                item.setdefault("workflow_id", record.get("workflow_id"))
                item["extensions"] = {"jsonl": record}
                items.append(item)
            elif record.get("event_type"):
                session_id = str(record.get("session_id") or "")
                if session_id:
                    span = sessions.get(session_id)
                    if span is None:
                        sessions[session_id] = _SessionSpan(record)
                    else:
                        span.add(record)
        for session_id, span in sessions.items():
            terminal = span.terminal
            campaign = str(terminal.get("trace_id") or terminal.get("workspace_id") or "")
            items.append(
                {
                    "workflow_id": session_id,
                    "campaign_id": campaign,
                    "name": f"CLIO session {session_id}",
                    "status": str(terminal.get("status") or ""),
                    "started_at": span.started_at,
                    "ended_at": span.ended_at,
                    "extensions": {"clio": {"event_count": span.count}},
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
        for record in self._records(all_of=(workflow_id,)):
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
        matches = self._tasks(
            workflow_id=workflow_id,
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            activity_id=activity_id,
            subtype=subtype,
        )
        # The earliest ``limit`` tasks, in the order a stable sort would give, holding
        # no more than ``limit`` of them at a time.
        items = heapq.nsmallest(
            _limit(limit), matches, key=lambda item: float(item.get("started_at") or 0)
        )
        return {"items": items, "count": len(items)}

    def _tasks(self, **filters: str | None) -> Iterator[dict[str, Any]]:
        """Stream the tasks matching every set filter (a task field equal to it)."""
        searched = tuple(value for key, value in filters.items() if key != "subtype")
        for record in self._records(all_of=searched):
            item = _task(record)
            if item is None:
                continue
            if all(not value or item[key] == value for key, value in filters.items()):
                yield item

    def summarize_tasks(self, workflow_id: str | None) -> dict[str, Any]:
        """Summarize native task status and activity counts over every matching task."""
        statuses: Counter[str] = Counter()
        activities: Counter[str] = Counter()
        for item in self._tasks(workflow_id=workflow_id):
            statuses[item["status"]] += 1
            activities[item["activity_id"]] += 1
        return {
            "workflow_id": workflow_id,
            "task_count": sum(statuses.values()),
            "status_counts": dict(sorted(statuses.items())),
            "activity_counts": dict(sorted(activities.items())),
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
            for record in self._records(all_of=("record_type", "pipeline"))
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
        limit = _limit(limit)
        for record in self._records(
            all_of=(pipeline, stage), any_of=("execution", "artifact.transform.recorded")
        ):
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
            if len(items) >= limit:
                break
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
        for record in self._records(all_of=(pipeline,), any_of=("artifact",)):
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
        for record in self._records(all_of=(pipeline,), any_of=("artifact.transform.recorded",)):
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
        for record in self._records(all_of=("model_card", model_id)):
            if (
                record.get("record_type") == "model_card"
                and str(record.get("model_id") or "") == model_id
            ):
                return dict(record.get("data") or {})
        raise capability_unavailable("get_model_card", self.name)

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]:
        """Find native records containing an exact correlation identifier."""
        matches: list[dict[str, Any]] = []
        for record in self._records(all_of=(correlation_id,)):
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


class _SessionSpan:
    """One CLIO session's first and last events, as a stable sort by time would order them."""

    __slots__ = ("count", "ended_at", "started_at", "terminal")

    def __init__(self, record: dict[str, Any]) -> None:
        self.count = 1
        self.started_at = self.ended_at = _timestamp(record)
        self.terminal = record

    def add(self, record: dict[str, Any]) -> None:
        self.count += 1
        occurred = _timestamp(record)
        self.started_at = min(self.started_at, occurred)
        if occurred >= self.ended_at:
            self.ended_at, self.terminal = occurred, record


_PLAIN = re.compile(r"[A-Za-z0-9_.:@+-]+")


def _needle(value: str) -> bytes | None:
    """The bytes any JSON line holding ``value`` (as a string or a number) contains.

    ``None`` for a value JSON may escape, which no line filter can rely on.
    """

    return value.encode() if _PLAIN.fullmatch(value) else None


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
