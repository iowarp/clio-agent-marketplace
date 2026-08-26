"""Direct, read-only CMF REST provenance queries."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from spotter_ai.config import CMFQueryConfig
from spotter_ai.errors import ProvenanceError

_CAPABILITIES = {
    "list_pipelines",
    "list_executions",
    "list_artifact_types",
    "list_artifacts",
    "get_execution_lineage",
    "get_artifact_lineage",
    "get_model_card",
    "trace_correlation",
}


class CMFProvider:
    """Query the CMF server API without using or proxying CMF's MCP."""

    name = "cmf"

    def __init__(self, config: CMFQueryConfig, *, client: httpx.Client | None = None) -> None:
        self._pipeline = config.pipeline_name
        self._client = client or httpx.Client(base_url=config.server_url, timeout=30.0)

    def capabilities(self) -> set[str]:
        """Return the CMF-backed Spotter operations."""
        return set(_CAPABILITIES)

    def health(self) -> dict[str, Any]:
        """Check that the CMF REST service can enumerate pipelines."""
        try:
            response = self._client.get("/api/pipelines")
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - provider boundary
            return {"provider": self.name, "status": "unavailable", "error": type(exc).__name__}
        return {"provider": self.name, "status": "ready", "pipeline": self._pipeline}

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - provider boundary
            raise ProvenanceError(
                "provider_unavailable",
                f"CMF REST query failed for {path}",
                {"provider": self.name, "path": path, "reason": type(exc).__name__},
            ) from exc

    def _selected_pipeline(self, pipeline: str | None) -> str:
        return (pipeline or self._pipeline).strip()

    def list_pipelines(self, limit: int) -> dict[str, Any]:
        """List CMF pipelines."""
        raw = self._get("/api/pipelines")
        names = [str(value) for value in raw if value] if isinstance(raw, list) else []
        items = [{"pipeline": name} for name in names[: _limit(limit)]]
        return {"items": items, "count": len(items)}

    def _stages(self, pipeline: str) -> list[str]:
        raw = self._get(f"/api/pipeline-stages/{quote(pipeline, safe='')}")
        if isinstance(raw, dict):
            return [str(value) for value in raw.get("stages") or [] if value]
        return []

    def list_executions(
        self, pipeline: str | None, stage: str | None, limit: int
    ) -> dict[str, Any]:
        """List CMF execution records across one or all pipeline stages."""
        selected = self._selected_pipeline(pipeline)
        stages = [stage] if stage else self._stages(selected)
        items: list[dict[str, Any]] = []
        for stage_name in stages:
            raw = self._get(
                f"/api/executions-by-stage/{quote(selected, safe='')}",
                params={
                    "stage_name": stage_name,
                    "active_page": 1,
                    "record_per_page": _limit(limit),
                    "sort_order": "DESC",
                    "filter_value": "",
                },
            )
            rows = raw.get("items") if isinstance(raw, dict) else []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                execution_id = _property(row, "Execution_uuid") or row.get("execution_id")
                items.append(
                    {
                        "execution_id": str(execution_id or ""),
                        "pipeline": selected,
                        "stage": str(stage_name),
                        "name": str(_property(row, "Execution") or row.get("name") or ""),
                        "status": str(_property(row, "clio_status") or row.get("status") or ""),
                        "extensions": {"cmf": row},
                    }
                )
                if len(items) >= _limit(limit):
                    return {"items": items, "count": len(items)}
        return {"items": items, "count": len(items)}

    def list_artifact_types(self, pipeline: str | None, stage: str | None) -> dict[str, Any]:
        """List CMF artifact types globally or within a pipeline stage."""
        if pipeline and stage:
            raw = self._get(
                f"/api/artifact-types-by-stage/{quote(pipeline, safe='')}",
                params={"stage_name": stage},
            )
        else:
            raw = self._get("/api/artifact_types")
        items = (
            [{"artifact_type": str(value)} for value in raw if value]
            if isinstance(raw, list)
            else []
        )
        return {"items": items, "count": len(items)}

    def list_artifacts(
        self,
        *,
        pipeline: str | None,
        stage: str | None,
        artifact_type: str | None,
        limit: int,
    ) -> dict[str, Any]:
        """List CMF artifacts across one or all stages and types."""
        selected = self._selected_pipeline(pipeline)
        stages = [stage] if stage else self._stages(selected)
        items: list[dict[str, Any]] = []
        for stage_name in stages:
            types = (
                [artifact_type]
                if artifact_type
                else [
                    row["artifact_type"]
                    for row in self.list_artifact_types(selected, stage_name)["items"]
                ]
            )
            for type_name in types:
                raw = self._get(
                    f"/api/artifacts-by-stage/{quote(selected, safe='')}",
                    params={
                        "stage_name": stage_name,
                        "artifact_type": type_name,
                        "active_page": 1,
                        "record_per_page": _limit(limit),
                        "sort_field": "name",
                        "sort_order": "asc",
                        "filter_value": "",
                    },
                )
                rows = raw.get("items") if isinstance(raw, dict) else []
                for row in rows if isinstance(rows, list) else []:
                    if not isinstance(row, dict):
                        continue
                    stable_id = _property(row, "clio_artifact_id") or row.get("artifact_id")
                    items.append(
                        {
                            "artifact_id": str(stable_id or ""),
                            "cmf_artifact_id": str(row.get("artifact_id") or ""),
                            "pipeline": selected,
                            "stage": str(stage_name),
                            "artifact_type": str(type_name),
                            "name": str(row.get("name") or _property(row, "clio_name") or ""),
                            "sha256": str(_property(row, "clio_sha256") or ""),
                            "uri": str(_property(row, "url") or ""),
                            "extensions": {"cmf": row},
                        }
                    )
                    if len(items) >= _limit(limit):
                        return {"items": items, "count": len(items)}
        return {"items": items, "count": len(items)}

    def execution_lineage(self, pipeline: str | None, execution_id: str) -> dict[str, Any]:
        """Fetch and normalize CMF execution lineage for one full UUID."""
        selected = self._selected_pipeline(pipeline)
        raw = self._get(
            f"/api/execution-lineage/tangled-tree/{quote(execution_id, safe='')}/"
            f"{quote(selected, safe='')}"
        )
        if not isinstance(raw, dict):
            raise ProvenanceError("not_found", f"CMF execution not found: {execution_id}")
        raw_nodes = raw.get("nodes")
        raw_links = raw.get("links")
        nodes: list[Any] = raw_nodes if isinstance(raw_nodes, list) else []
        links: list[Any] = raw_links if isinstance(raw_links, list) else []
        return {
            "root": execution_id,
            "pipeline": selected,
            "nodes": nodes,
            "edges": [
                {
                    "source": str(link.get("source")),
                    "target": str(link.get("target")),
                    "kind": "lineage",
                }
                for link in links
                if isinstance(link, dict)
            ],
            "extensions": {"cmf": raw},
        }

    def artifact_lineage(self, pipeline: str | None, artifact_id: str) -> dict[str, Any]:
        """Fetch CMF's layered artifact lineage and project it to nodes and edges."""
        selected = self._selected_pipeline(pipeline)
        raw = self._get(f"/api/artifact-lineage/tangled-tree/{quote(selected, safe='')}")
        layers = raw if isinstance(raw, list) else []
        artifact_rows = self.list_artifacts(
            pipeline=selected,
            stage=None,
            artifact_type=None,
            limit=10_000,
        )["items"]
        aliases: dict[str, list[str]] = {}
        requested_display_id = ""
        for artifact in artifact_rows:
            stable_id = str(artifact.get("artifact_id") or "")
            display_id = _lineage_display_id(
                str(artifact.get("name") or ""),
                str(artifact.get("artifact_type") or ""),
            )
            if stable_id and display_id:
                aliases.setdefault(display_id, []).append(stable_id)
            if stable_id == artifact_id:
                requested_display_id = display_id

        def stable_node_id(display_id: str) -> str:
            candidates = aliases.get(display_id, [])
            if display_id == requested_display_id:
                return artifact_id
            return candidates[0] if len(candidates) == 1 else display_id

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        for depth, layer in enumerate(layers):
            for row in layer if isinstance(layer, list) else []:
                if not isinstance(row, dict):
                    continue
                display_id = str(row.get("id") or "")
                node_id = stable_node_id(display_id)
                nodes.append(
                    {
                        "id": node_id,
                        "type": "artifact",
                        "depth": depth,
                        "extensions": {"cmf": {"display_id": display_id}},
                    }
                )
                edges.extend(
                    {
                        "source": stable_node_id(str(parent)),
                        "target": node_id,
                        "kind": "generated",
                    }
                    for parent in row.get("parents") or []
                )
        matching = [node for node in nodes if node["id"] == artifact_id]
        if artifact_id and not matching:
            raise ProvenanceError(
                "not_found",
                f"CMF artifact was not present in pipeline lineage: {artifact_id}",
                {"pipeline": selected},
            )
        root = matching[0]["id"] if matching else ""
        return {
            "root": root,
            "pipeline": selected,
            "nodes": nodes,
            "edges": edges,
            "truncated": None,
            "extensions": {"cmf": {"layers": raw}},
        }

    def model_card(self, model_id: str) -> dict[str, Any]:
        """Return CMF's four model-card evidence sections with stable labels."""
        raw = self._get("/api/model-card", params={"modelId": model_id})
        if not isinstance(raw, list) or len(raw) != 4:
            raise ProvenanceError("not_found", f"CMF model card not found: {model_id}")
        return {
            "model_id": model_id,
            "model": raw[0],
            "execution": raw[1],
            "inputs": raw[2],
            "outputs": raw[3],
        }

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]:
        """Find CMF execution or artifact rows containing a CLIO correlation value."""
        matches: list[dict[str, Any]] = []
        executions = self.list_executions(None, None, limit)["items"]
        artifacts = self.list_artifacts(pipeline=None, stage=None, artifact_type=None, limit=limit)[
            "items"
        ]
        for kind, row in [("execution", item) for item in executions] + [
            ("artifact", item) for item in artifacts
        ]:
            if correlation_id in json.dumps(row, sort_keys=True, default=str):
                matches.append({"kind": kind, **row})
                if len(matches) >= _limit(limit):
                    break
        return matches

    def close(self) -> None:
        """Close the CMF HTTP client."""
        self._client.close()


def _property(row: dict[str, Any], name: str) -> Any:
    direct = row.get(name)
    if direct is not None:
        return direct
    for container_name in ("artifact_properties", "execution_properties", "properties"):
        container = row.get(container_name)
        if isinstance(container, dict) and name in container:
            return container[name]
        if isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                key = item.get("name") or item.get("key")
                if key == name:
                    return item.get("value")
    for prefix in ("custom_properties_", "properties_"):
        if f"{prefix}{name}" in row:
            return row[f"{prefix}{name}"]
    return None


def _lineage_display_id(name: str, artifact_type: str) -> str:
    """Reproduce the artifact labels emitted by CMF's tangled-tree endpoint."""
    try:
        split_by_colon = name.split(":")
        if artifact_type == "Metrics":
            return f"{split_by_colon[0]}:{split_by_colon[1][:4]}:{split_by_colon[2]}"
        if artifact_type == "Model":
            return f"{split_by_colon[-3].split('/')[-1]}:{split_by_colon[-2][:4]}"
        if artifact_type == "Dataset":
            artifact_path = name.rsplit(":")[0]
            parts = artifact_path.split("/")
            artifact_name = parts[-1] or parts[-2]
            return f"{artifact_name}:{split_by_colon[-1][:4]}"
        if artifact_type == "Dataslice":
            relative = name.split("/", 1)[1]
            path, lineage_id = relative.rsplit(":", 1)
            return f"{path}:{lineage_id[:4]}"
        if artifact_type == "Step_Metrics":
            relative = name.split("/", 1)[1]
            values = name.rsplit(":")
            return f"{relative.rsplit(':', 3)[0]}:{values[-3][:4]}:{values[-2]}:{values[-1][:4]}"
    except (IndexError, ValueError):
        return name
    return name


def _limit(value: int) -> int:
    return max(1, min(int(value), 10_000))
