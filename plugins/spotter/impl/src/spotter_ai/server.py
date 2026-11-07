"""Standalone Spotter provenance MCP backed directly by configured stores."""

from __future__ import annotations

import argparse
import atexit
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from clio_schemas.attention import AttentionProfile
from fastmcp import FastMCP

from spotter_ai.attention import AttentionEvidence
from spotter_ai.config import SpotterConfig, load_config
from spotter_ai.errors import ProvenanceError
from spotter_ai.providers.factory import create_providers
from spotter_ai.providers.flowcept import FlowceptProvider
from spotter_ai.service import ProvenanceService

_READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


#: The raw provenance tools SPOTTER's watcher is offered: Flowcept's task records for
#: the watched session, and a correlation trace across them. Its routine review runs on
#: CLIO's review_activity and attention_sources; listing, lineage and timeline tools only
#: multiplied the menu a small model has to choose from.
WATCHER_TOOLS = frozenset({"query_tasks", "trace_correlation"})


def _invoke[Result](callback: Callable[[], Result]) -> Result:
    """Translate provider errors to stable JSON FastMCP errors."""
    try:
        return callback()
    except ProvenanceError as exc:
        raise exc.as_tool_error() from exc


def _operations(provider: Any) -> frozenset[str] | None:
    """A provider's operations at startup, or ``None`` when its store cannot say yet.

    ``None`` serves the domain's tools unconditionally: each call then reports
    the store's own typed error instead of the tool silently disappearing.
    """
    try:
        return frozenset(provider.capabilities())
    except ProvenanceError:
        return None


def create_server(
    config: SpotterConfig | str | Path | None = None,
    *,
    service: ProvenanceService | None = None,
    attention: AttentionEvidence | None = None,
) -> FastMCP:
    """Build the provider-aware provenance and captured-attention Spotter tools."""
    resolved = (
        config
        if isinstance(config, SpotterConfig)
        else (load_config(config) if config or service is None else None)
    )
    if service is None:
        assert resolved is not None
        service = ProvenanceService(*create_providers(resolved))
    if attention is None and resolved and resolved.attention_files_dir and resolved.flowcept:
        reader = FlowceptProvider(resolved.flowcept)
        atexit.register(reader.close)
        attention = AttentionEvidence(reader, resolved.attention_files_dir)
    active = service
    mcp = FastMCP("spotter")

    def tool(**kwargs: Any) -> Callable[[Callable[..., Any]], Any]:
        """Serve only the watcher's provenance tools (see :data:`WATCHER_TOOLS`)."""
        register = mcp.tool(**kwargs)
        return lambda func: register(func) if func.__name__ in WATCHER_TOOLS else func

    artifact_ops = _operations(active.artifact)
    agentic_ops = _operations(active.agentic)

    def artifact_tool(
        operation: str, title: str, *, agentic: bool = False
    ) -> Callable[[Callable[..., Any]], Any]:
        """Serve an artifact-lineage tool only when the configured provider answers it.

        A tool the active artifact provider (and, for joins, the agentic one)
        cannot answer would only invite ``capability_unavailable`` round trips,
        so it is left off the menu; ``capabilities`` still names every provider
        operation, and a store that cannot answer is never silently substituted.
        """
        if (artifact_ops is not None and operation not in artifact_ops) or (
            agentic and agentic_ops is not None and operation not in agentic_ops
        ):
            return lambda func: func
        return tool(title=title, annotations=_READ_ONLY_ANNOTATIONS)

    def answer(domain: Literal["agentic", "artifact"], callback: Callable[[], Any]) -> Any:
        """Stamp a query result with the lane that answered it, never silently."""
        result = _invoke(callback)
        provider = active.agentic if domain == "agentic" else active.artifact
        lane: dict[str, Any] = {"domain": domain, "provider": provider.name}
        if domain == "agentic" and resolved is not None:
            lane["selected_by"] = resolved.agentic_selected_by
            if (
                resolved.agentic_selected_by == "default_jsonl"
                and resolved.agentic_alternatives
                and isinstance(result, dict)
                and result.get("items") == []
            ):
                lane["hint"] = (
                    "lane_defaulted: "
                    + ", ".join(resolved.agentic_alternatives)
                    + " is enabled but not the query lane; set provenance.agentic.query_default"
                )
        return {**result, "lane": lane} if isinstance(result, dict) else result

    @tool(title="Inspect provenance capabilities", annotations=_READ_ONLY_ANNOTATIONS)
    def capabilities() -> dict[str, Any]:
        """Report active agentic/artifact providers, health, and exact operations."""
        described = active.capabilities()
        if resolved is not None:  # say how the query lane was chosen, never silently
            described["agentic"] = {
                **described["agentic"],
                "selected_by": resolved.agentic_selected_by,
                "enabled_not_queried": list(resolved.agentic_alternatives),
            }
        return {
            **described,
            "attention": {
                "configured": attention is not None,
                "verified": False,
                "requires": "Flowcept and an explicit local capture directory",
            },
        }

    def require_attention() -> AttentionEvidence:
        if attention is None:
            raise ProvenanceError(
                "attention_not_configured", "Configure Flowcept and provenance.attention.files_dir"
            )
        return attention

    @tool(title="List captured model-call identities", annotations=_READ_ONLY_ANNOTATIONS)
    def list_attention_calls(session_id: str, limit: int = 100) -> dict[str, Any]:
        """Find model response IDs with ``capture_available`` and ``decode_steps`` per call;
        listing does not verify the capture file itself."""
        return _invoke(lambda: require_attention().list_calls(session_id, limit))

    @tool(title="Inspect captured attention", annotations=_READ_ONLY_ANNOTATIONS)
    def inspect_attention(
        response_id: str,
        steps: list[int] | None = None,
        profile: AttentionProfile | None = None,
    ) -> dict[str, Any]:
        """Read verified local capture rows with CLIO's versioned profile semantics.

        Omit ``steps`` to inspect the whole response. To narrow it, pass decode-step
        indices within ``0..decode_steps-1`` (``list_attention_calls`` reports
        ``decode_steps`` per response), never estimated character or image
        coordinates. Returns evidence, coverage and uncertainty; it changes nothing.
        """
        return _invoke(
            lambda: require_attention().inspect(response_id, steps, profile or AttentionProfile())
        )

    @tool(title="List provenance campaigns", annotations=_READ_ONLY_ANNOTATIONS)
    def list_campaigns(campaign_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List distributed campaign groupings from the agentic provider."""
        return answer(
            "agentic",
            lambda: active.require_agentic("list_campaigns").list_campaigns(campaign_id, limit),
        )

    @tool(title="List workflow executions", annotations=_READ_ONLY_ANNOTATIONS)
    def list_workflows(
        campaign_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List workflow executions, optionally filtered by campaign and status."""
        return answer(
            "agentic",
            lambda: active.require_agentic("list_workflows").list_workflows(
                campaign_id, status, limit
            ),
        )

    @tool(title="List workflow agents", annotations=_READ_ONLY_ANNOTATIONS)
    def list_agents(workflow_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List agents recorded globally or within one workflow."""
        return answer(
            "agentic", lambda: active.require_agentic("list_agents").list_agents(workflow_id, limit)
        )

    @tool(title="Query execution tasks", annotations=_READ_ONLY_ANNOTATIONS)
    def query_tasks(
        workflow_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        status: str | None = None,
        activity_id: str | None = None,
        subtype: str | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        """Query task and agent-action records with Flowcept-shaped filters."""
        return answer(
            "agentic",
            lambda: active.require_agentic("query_tasks").query_tasks(
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent_id,
                status=status,
                activity_id=activity_id,
                subtype=subtype,
                limit=limit,
            ),
        )

    @tool(title="Summarize execution tasks", annotations=_READ_ONLY_ANNOTATIONS)
    def summarize_tasks(workflow_id: str | None = None) -> dict[str, Any]:
        """Aggregate task status, activity, duration, and time-range evidence."""
        return answer(
            "agentic",
            lambda: active.require_agentic("summarize_tasks").summarize_tasks(workflow_id),
        )

    @tool(title="Get execution timeline graph", annotations=_READ_ONLY_ANNOTATIONS)
    def get_timeline(workflow_id: str, limit: int = 1000) -> dict[str, Any]:
        """Return spans plus parent/dependency nodes and edges for one workflow."""
        return answer(
            "agentic", lambda: active.require_agentic("get_timeline").timeline(workflow_id, limit)
        )

    @artifact_tool("list_pipelines", "List artifact pipelines")
    def list_pipelines(limit: int = 100) -> dict[str, Any]:
        """List artifact-lineage pipelines known to the artifact provider."""
        return answer(
            "artifact", lambda: active.require_artifact("list_pipelines").list_pipelines(limit)
        )

    @artifact_tool("list_executions", "List pipeline executions")
    def list_executions(
        pipeline: str | None = None,
        stage: str | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        """List artifact-producing executions, optionally within one stage."""
        return answer(
            "artifact",
            lambda: active.require_artifact("list_executions").list_executions(
                pipeline, stage, limit
            ),
        )

    @artifact_tool("list_artifact_types", "List artifact types")
    def list_artifact_types(
        pipeline: str | None = None, stage: str | None = None
    ) -> dict[str, Any]:
        """List artifact types globally or in a selected pipeline stage."""
        return answer(
            "artifact",
            lambda: active.require_artifact("list_artifact_types").list_artifact_types(
                pipeline, stage
            ),
        )

    @artifact_tool("list_artifacts", "List provenance artifacts")
    def list_artifacts(
        pipeline: str | None = None,
        stage: str | None = None,
        artifact_type: str | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        """List artifacts using CMF pipeline/stage/type semantics when available."""
        return answer(
            "artifact",
            lambda: active.require_artifact("list_artifacts").list_artifacts(
                pipeline=pipeline,
                stage=stage,
                artifact_type=artifact_type,
                limit=limit,
            ),
        )

    @artifact_tool("get_execution_lineage", "Get execution lineage")
    def get_execution_lineage(execution_id: str, pipeline: str | None = None) -> dict[str, Any]:
        """Return the artifact graph rooted at one producing execution."""
        return answer(
            "artifact",
            lambda: active.require_artifact("get_execution_lineage").execution_lineage(
                pipeline, execution_id
            ),
        )

    @artifact_tool("get_artifact_lineage", "Get artifact lineage")
    def get_artifact_lineage(artifact_id: str, pipeline: str | None = None) -> dict[str, Any]:
        """Return the artifact graph rooted at one stable artifact identifier."""
        return answer(
            "artifact",
            lambda: active.require_artifact("get_artifact_lineage").artifact_lineage(
                pipeline, artifact_id
            ),
        )

    @artifact_tool("get_model_card", "Get model card evidence")
    def get_model_card(model_id: str) -> dict[str, Any]:
        """Return recorded model, execution, input, and output evidence."""
        return answer(
            "artifact", lambda: active.require_artifact("get_model_card").model_card(model_id)
        )

    @artifact_tool("trace_correlation", "Trace cross-provider correlation", agentic=True)
    def trace_correlation(correlation_id: str, limit: int = 100) -> dict[str, Any]:
        """Join agentic and artifact evidence using an exact CLIO correlation id."""
        return _invoke(lambda: active.trace_correlation(correlation_id, limit))

    return mcp


def main() -> None:
    """Serve Spotter over stdio using the explicitly selected CLIO config."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clio-config", type=Path, help="CLIO YAML configuration path")
    arguments = parser.parse_args()
    resolved = load_config(arguments.clio_config)
    service = ProvenanceService(*create_providers(resolved))
    atexit.register(service.close)
    create_server(resolved, service=service).run()


if __name__ == "__main__":
    main()
