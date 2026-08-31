"""Standalone Spotter provenance MCP backed directly by configured stores."""

from __future__ import annotations

import argparse
import atexit
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from spotter_ai.campaign import CampaignForensics, stable_tool_annotations, validate_reason
from spotter_ai.config import SpotterConfig, load_config
from spotter_ai.errors import ProvenanceError
from spotter_ai.providers.factory import create_providers
from spotter_ai.service import ProvenanceService

_READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def _invoke[Result](callback: Callable[[], Result]) -> Result:
    """Translate provider errors to stable JSON FastMCP errors."""
    try:
        return callback()
    except ProvenanceError as exc:
        raise exc.as_tool_error() from exc


def create_server(
    config: SpotterConfig | str | Path | None = None,
    *,
    service: ProvenanceService | None = None,
    campaign: CampaignForensics | None = None,
) -> FastMCP:
    """Build provider-aware and campaign-forensic Spotter tools in one server."""
    if service is None:
        resolved = config if isinstance(config, SpotterConfig) else load_config(config)
        service = ProvenanceService(*create_providers(resolved))
    active = service
    active_campaign = campaign or CampaignForensics()
    mcp = FastMCP("spotter")

    @mcp.tool(title="Inspect provenance capabilities", annotations=_READ_ONLY_ANNOTATIONS)
    def capabilities() -> dict[str, Any]:
        """Report active agentic/artifact providers, health, and exact operations."""
        return {**active.capabilities(), "campaign_forensics": active_campaign.capabilities()}

    @mcp.tool(title="List campaign runs", annotations=stable_tool_annotations(read_only=True))
    def list_runs() -> dict[str, Any]:
        """List phenotype runs, metrics, and recorded graph cardinality."""
        return _invoke(active_campaign.list_runs)

    @mcp.tool(title="Run health check", annotations=stable_tool_annotations(read_only=True))
    def run_health(run_id: str) -> dict[str, Any]:
        """Score one phenotype run against the campaign's completed peers."""
        return _invoke(lambda: active_campaign.run_health(run_id))

    @mcp.tool(title="Campaign health sweep", annotations=stable_tool_annotations(read_only=True))
    def campaign_health() -> dict[str, Any]:
        """Sweep all completed phenotype runs in one bounded call."""
        return _invoke(active_campaign.campaign_health)

    @mcp.tool(title="Compare two runs", annotations=stable_tool_annotations(read_only=True))
    def diff_runs(run_id: str, baseline_run_id: str) -> dict[str, Any]:
        """Compare two phenotype runs stage by stage without hiding discrepancies."""
        return _invoke(lambda: active_campaign.diff_runs(run_id, baseline_run_id))

    @mcp.tool(title="Trace run lineage", annotations=stable_tool_annotations(read_only=True))
    def trace_lineage(run_id: str, stage: str | None = None) -> dict[str, Any]:
        """Trace one phenotype run's exact stage and artifact chain."""
        return _invoke(lambda: active_campaign.trace_lineage(run_id, stage))

    @mcp.tool(title="Read provenance artifact", annotations=stable_tool_annotations(read_only=True))
    def read_artifact(artifact_id: int) -> dict[str, Any]:
        """Read one exact phenotype artifact with bounded content."""
        return _invoke(lambda: active_campaign.read_artifact(artifact_id))

    @mcp.tool(title="Raise anomaly alert", annotations=stable_tool_annotations(read_only=False))
    def raise_alert(run_id: str, reason: str) -> dict[str, Any]:
        """Quarantine the phenotype campaign after validating the implicated run."""
        return _invoke(lambda: active_campaign.raise_alert(run_id, validate_reason(reason)))

    @mcp.tool(title="Lift quarantine", annotations=stable_tool_annotations(read_only=False))
    def lift_quarantine() -> dict[str, Any]:
        """Resume the phenotype campaign after explicit human authorization."""
        return _invoke(active_campaign.lift_quarantine)

    @mcp.tool(title="List provenance campaigns", annotations=_READ_ONLY_ANNOTATIONS)
    def list_campaigns(campaign_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List distributed campaign groupings from the agentic provider."""
        return _invoke(
            lambda: active.require_agentic("list_campaigns").list_campaigns(campaign_id, limit)
        )

    @mcp.tool(title="List workflow executions", annotations=_READ_ONLY_ANNOTATIONS)
    def list_workflows(
        campaign_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List workflow executions, optionally filtered by campaign and status."""
        return _invoke(
            lambda: active.require_agentic("list_workflows").list_workflows(
                campaign_id, status, limit
            )
        )

    @mcp.tool(title="List workflow agents", annotations=_READ_ONLY_ANNOTATIONS)
    def list_agents(workflow_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List agents recorded globally or within one workflow."""
        return _invoke(
            lambda: active.require_agentic("list_agents").list_agents(workflow_id, limit)
        )

    @mcp.tool(title="Query execution tasks", annotations=_READ_ONLY_ANNOTATIONS)
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
        return _invoke(
            lambda: active.require_agentic("query_tasks").query_tasks(
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent_id,
                status=status,
                activity_id=activity_id,
                subtype=subtype,
                limit=limit,
            )
        )

    @mcp.tool(title="Summarize execution tasks", annotations=_READ_ONLY_ANNOTATIONS)
    def summarize_tasks(workflow_id: str | None = None) -> dict[str, Any]:
        """Aggregate task status, activity, duration, and time-range evidence."""
        return _invoke(
            lambda: active.require_agentic("summarize_tasks").summarize_tasks(workflow_id)
        )

    @mcp.tool(title="Get execution timeline graph", annotations=_READ_ONLY_ANNOTATIONS)
    def get_timeline(workflow_id: str, limit: int = 1000) -> dict[str, Any]:
        """Return spans plus parent/dependency nodes and edges for one workflow."""
        return _invoke(lambda: active.require_agentic("get_timeline").timeline(workflow_id, limit))

    @mcp.tool(title="List artifact pipelines", annotations=_READ_ONLY_ANNOTATIONS)
    def list_pipelines(limit: int = 100) -> dict[str, Any]:
        """List artifact-lineage pipelines known to the artifact provider."""
        return _invoke(lambda: active.require_artifact("list_pipelines").list_pipelines(limit))

    @mcp.tool(title="List pipeline executions", annotations=_READ_ONLY_ANNOTATIONS)
    def list_executions(
        pipeline: str | None = None,
        stage: str | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        """List artifact-producing executions, optionally within one stage."""
        return _invoke(
            lambda: active.require_artifact("list_executions").list_executions(
                pipeline, stage, limit
            )
        )

    @mcp.tool(title="List artifact types", annotations=_READ_ONLY_ANNOTATIONS)
    def list_artifact_types(
        pipeline: str | None = None, stage: str | None = None
    ) -> dict[str, Any]:
        """List artifact types globally or in a selected pipeline stage."""
        return _invoke(
            lambda: active.require_artifact("list_artifact_types").list_artifact_types(
                pipeline, stage
            )
        )

    @mcp.tool(title="List provenance artifacts", annotations=_READ_ONLY_ANNOTATIONS)
    def list_artifacts(
        pipeline: str | None = None,
        stage: str | None = None,
        artifact_type: str | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        """List artifacts using CMF pipeline/stage/type semantics when available."""
        return _invoke(
            lambda: active.require_artifact("list_artifacts").list_artifacts(
                pipeline=pipeline,
                stage=stage,
                artifact_type=artifact_type,
                limit=limit,
            )
        )

    @mcp.tool(title="Get execution lineage", annotations=_READ_ONLY_ANNOTATIONS)
    def get_execution_lineage(execution_id: str, pipeline: str | None = None) -> dict[str, Any]:
        """Return the artifact graph rooted at one producing execution."""
        return _invoke(
            lambda: active.require_artifact("get_execution_lineage").execution_lineage(
                pipeline, execution_id
            )
        )

    @mcp.tool(title="Get artifact lineage", annotations=_READ_ONLY_ANNOTATIONS)
    def get_artifact_lineage(artifact_id: str, pipeline: str | None = None) -> dict[str, Any]:
        """Return the artifact graph rooted at one stable artifact identifier."""
        return _invoke(
            lambda: active.require_artifact("get_artifact_lineage").artifact_lineage(
                pipeline, artifact_id
            )
        )

    @mcp.tool(title="Get model card evidence", annotations=_READ_ONLY_ANNOTATIONS)
    def get_model_card(model_id: str) -> dict[str, Any]:
        """Return recorded model, execution, input, and output evidence."""
        return _invoke(lambda: active.require_artifact("get_model_card").model_card(model_id))

    @mcp.tool(title="Trace cross-provider correlation", annotations=_READ_ONLY_ANNOTATIONS)
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
