"""Direct, read-only Flowcept MongoDB provenance queries."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from spotter_ai.config import FlowceptQueryConfig
from spotter_ai.errors import ProvenanceError

_CAPABILITIES = {
    "list_campaigns",
    "list_workflows",
    "list_agents",
    "query_tasks",
    "summarize_tasks",
    "get_timeline",
    "trace_correlation",
}


class FlowceptProvider:
    """Query Flowcept's documented workflow/task collections without its MCP."""

    name = "flowcept"

    def __init__(self, config: FlowceptQueryConfig, *, client: Any | None = None) -> None:
        self._client: MongoClient[Any] = client or MongoClient(
            config.uri,
            serverSelectionTimeoutMS=5_000,
            connectTimeoutMS=5_000,
            socketTimeoutMS=15_000,
        )
        self._database = self._client[config.database]

    def capabilities(self) -> set[str]:
        """Return the Flowcept-backed Spotter operations."""
        return set(_CAPABILITIES)

    def health(self) -> dict[str, Any]:
        """Check MongoDB without exposing credentials."""
        try:
            self._client.admin.command("ping")
        except Exception as exc:  # noqa: BLE001 - provider boundary
            return {"provider": self.name, "status": "unavailable", "error": type(exc).__name__}
        return {"provider": self.name, "status": "ready", "database": self._database.name}

    def _collection(self, name: str) -> Collection[dict[str, Any]]:
        return self._database[name]

    def _guard(self, operation: str, callback: Any) -> Any:
        try:
            return callback()
        except ProvenanceError:
            raise
        except Exception as exc:  # noqa: BLE001 - provider boundary
            raise ProvenanceError(
                "provider_unavailable",
                f"Flowcept MongoDB query failed during {operation}",
                {"provider": self.name, "operation": operation, "reason": type(exc).__name__},
            ) from exc

    def list_campaigns(self, campaign_id: str | None, limit: int) -> dict[str, Any]:
        """Derive campaign summaries from Flowcept workflow records."""

        def query() -> dict[str, Any]:
            match = (
                {"campaign_id": campaign_id}
                if campaign_id
                else {"campaign_id": {"$nin": [None, ""]}}
            )
            pipeline = [
                {"$match": match},
                {
                    "$group": {
                        "_id": "$campaign_id",
                        "workflow_count": {"$sum": 1},
                        "started_at": {"$min": "$started_at"},
                        "ended_at": {"$max": "$ended_at"},
                        "statuses": {"$addToSet": "$status"},
                    }
                },
                {"$sort": {"started_at": -1}},
                {"$limit": _limit(limit)},
            ]
            items = []
            for row in self._collection("workflows").aggregate(pipeline):
                items.append(
                    {
                        "campaign_id": str(row.get("_id") or ""),
                        "workflow_count": int(row.get("workflow_count") or 0),
                        "started_at": _public(row.get("started_at")),
                        "ended_at": _public(row.get("ended_at")),
                        "statuses": sorted(str(value) for value in row.get("statuses") or []),
                    }
                )
            return {"items": items, "count": len(items)}

        return self._guard("list_campaigns", query)

    def list_workflows(
        self, campaign_id: str | None, status: str | None, limit: int
    ) -> dict[str, Any]:
        """List Flowcept workflow executions."""
        query_filter = _present_filter(campaign_id=campaign_id, status=status)

        def query() -> dict[str, Any]:
            rows = (
                self._collection("workflows")
                .find(query_filter)
                .sort("started_at", -1)
                .limit(_limit(limit))
            )
            items = [_workflow(row) for row in rows]
            return {"items": items, "count": len(items)}

        return self._guard("list_workflows", query)

    def list_agents(self, workflow_id: str | None, limit: int) -> dict[str, Any]:
        """List agents stored explicitly or observed on Flowcept tasks."""

        def query() -> dict[str, Any]:
            query_filter = {"workflow_id": workflow_id} if workflow_id else {}
            rows = list(self._collection("agents").find(query_filter).limit(_limit(limit)))
            if rows:
                items = [
                    {
                        "agent_id": str(row.get("agent_id") or ""),
                        "name": str(row.get("name") or row.get("agent_id") or ""),
                        "workflow_id": str(row.get("workflow_id") or ""),
                        "campaign_id": str(row.get("campaign_id") or ""),
                        "extensions": {"flowcept": _public(row)},
                    }
                    for row in rows
                ]
            else:
                ids = self._collection("tasks").distinct("agent_id", query_filter)
                items = [{"agent_id": str(value), "name": str(value)} for value in ids if value]
                items = items[: _limit(limit)]
            return {"items": items, "count": len(items)}

        return self._guard("list_agents", query)

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
        """Query Flowcept tasks using a bounded typed filter."""
        query_filter = _present_filter(
            workflow_id=workflow_id,
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            activity_id=activity_id,
            subtype=subtype,
        )

        def query() -> dict[str, Any]:
            rows = (
                self._collection("tasks")
                .find(query_filter)
                .sort([("started_at", ASCENDING), ("utc_timestamp", ASCENDING)])
                .limit(_limit(limit))
            )
            items = [_task(row) for row in rows]
            return {"items": items, "count": len(items)}

        return self._guard("query_tasks", query)

    def summarize_tasks(self, workflow_id: str | None) -> dict[str, Any]:
        """Summarize task statuses, activities, durations, and time range."""

        def query() -> dict[str, Any]:
            query_filter = {"workflow_id": workflow_id} if workflow_id else {}
            rows = list(self._collection("tasks").find(query_filter).limit(10_000))
            statuses = Counter(str(row.get("status") or "unknown") for row in rows)
            activities = Counter(str(row.get("activity_id") or "unknown") for row in rows)
            durations = [
                float(row["ended_at"]) - float(row["started_at"])
                for row in rows
                if _number(row.get("started_at")) is not None
                and _number(row.get("ended_at")) is not None
            ]
            starts = [
                float(row["started_at"])
                for row in rows
                if _number(row.get("started_at")) is not None
            ]
            ends = [
                float(row["ended_at"]) for row in rows if _number(row.get("ended_at")) is not None
            ]
            return {
                "workflow_id": workflow_id,
                "task_count": len(rows),
                "status_counts": dict(sorted(statuses.items())),
                "activity_counts": dict(sorted(activities.items())),
                "duration_s": {
                    "total": sum(durations),
                    "average": sum(durations) / len(durations) if durations else None,
                },
                "time_range": {
                    "started_at": min(starts) if starts else None,
                    "ended_at": max(ends) if ends else None,
                },
            }

        return self._guard("summarize_tasks", query)

    def timeline(self, workflow_id: str, limit: int) -> dict[str, Any]:
        """Return a provider-neutral execution graph for timeline/Gantt/graph reasoning."""
        result = self.query_tasks(
            workflow_id=workflow_id,
            task_id=None,
            agent_id=None,
            status=None,
            activity_id=None,
            subtype=None,
            limit=limit,
        )
        spans = result["items"]
        nodes = [
            {
                "id": item["task_id"],
                "kind": item["subtype"] or "task",
                "label": item["activity_id"] or item["task_id"],
                "status": item["status"],
                "agent_id": item["agent_id"],
                "started_at": item["started_at"],
                "ended_at": item["ended_at"],
            }
            for item in spans
        ]
        task_ids = {str(item["task_id"]) for item in spans}
        edges: list[dict[str, Any]] = []
        for item in spans:
            parent = str(item.get("parent_task_id") or "")
            if parent and parent in task_ids:
                edges.append({"source": parent, "target": item["task_id"], "kind": "parent"})
            for dependency in item.get("dependencies") or []:
                if str(dependency) in task_ids:
                    edges.append(
                        {"source": str(dependency), "target": item["task_id"], "kind": "depends_on"}
                    )
        return {
            "workflow_id": workflow_id,
            "spans": spans,
            "nodes": nodes,
            "edges": edges,
            "complete": len(spans) < _limit(limit),
            "truncated": len(spans) >= _limit(limit),
        }

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]:
        """Find Flowcept tasks carrying one producer correlation identifier."""

        def query() -> list[dict[str, Any]]:
            variants = [
                {"custom_metadata.clio.correlation_id": correlation_id},
                {"custom_metadata.clio.session_id": correlation_id},
                {"custom_metadata.clio.turn_id": correlation_id},
                {"task_id": correlation_id},
            ]
            rows = self._collection("tasks").find({"$or": variants}).limit(_limit(limit))
            return [_task(row) for row in rows]

        return self._guard("trace_correlation", query)

    def close(self) -> None:
        """Close the MongoDB client."""
        self._client.close()


def _workflow(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": str(row.get("workflow_id") or ""),
        "parent_workflow_id": str(row.get("parent_workflow_id") or ""),
        "campaign_id": str(row.get("campaign_id") or ""),
        "name": str(row.get("name") or ""),
        "status": str(row.get("status") or ""),
        "subtype": str(row.get("subtype") or ""),
        "started_at": _number(row.get("started_at")),
        "ended_at": _number(row.get("ended_at")),
        "extensions": {"flowcept": _public(row)},
    }


def _task(row: dict[str, Any]) -> dict[str, Any]:
    start = _number(row.get("started_at"))
    end = _number(row.get("ended_at"))
    metadata = row.get("custom_metadata")
    clio = metadata.get("clio") if isinstance(metadata, dict) else {}
    clio = clio if isinstance(clio, dict) else {}
    return {
        "task_id": str(row.get("task_id") or ""),
        "parent_task_id": str(row.get("parent_task_id") or ""),
        "workflow_id": str(row.get("workflow_id") or ""),
        "campaign_id": str(row.get("campaign_id") or ""),
        "agent_id": str(row.get("agent_id") or ""),
        "source_agent_id": str(row.get("source_agent_id") or ""),
        "activity_id": str(row.get("activity_id") or ""),
        "subtype": str(row.get("subtype") or ""),
        "status": str(row.get("status") or ""),
        "started_at": start,
        "ended_at": end,
        "duration_ms": (end - start) * 1000 if start is not None and end is not None else None,
        "dependencies": [str(value) for value in row.get("dependencies") or []],
        "correlation_id": str(clio.get("correlation_id") or ""),
        "session_id": str(clio.get("session_id") or ""),
        "turn_id": str(clio.get("turn_id") or ""),
        "extensions": {"flowcept": _public(row)},
    }


def _present_filter(**values: str | None) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None and value != ""}


def _limit(value: int) -> int:
    return max(1, min(int(value), 10_000))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _public(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _public(item) for key, item in value.items() if key not in {"_id", "data"}
        }
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return None
    return str(value)
