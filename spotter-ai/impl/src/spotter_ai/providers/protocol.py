"""Provider contracts for the Spotter query plane."""

from __future__ import annotations

from typing import Any, Protocol


class AgenticProvider(Protocol):
    """Agent/workflow provenance queries."""

    name: str

    def health(self) -> dict[str, Any]: ...

    def capabilities(self) -> set[str]: ...

    def list_campaigns(self, campaign_id: str | None, limit: int) -> dict[str, Any]: ...

    def list_workflows(
        self, campaign_id: str | None, status: str | None, limit: int
    ) -> dict[str, Any]: ...

    def list_agents(self, workflow_id: str | None, limit: int) -> dict[str, Any]: ...

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
    ) -> dict[str, Any]: ...

    def summarize_tasks(self, workflow_id: str | None) -> dict[str, Any]: ...

    def timeline(self, workflow_id: str, limit: int) -> dict[str, Any]: ...

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


class ArtifactProvider(Protocol):
    """Artifact/pipeline provenance queries."""

    name: str

    def health(self) -> dict[str, Any]: ...

    def capabilities(self) -> set[str]: ...

    def list_pipelines(self, limit: int) -> dict[str, Any]: ...

    def list_executions(
        self, pipeline: str | None, stage: str | None, limit: int
    ) -> dict[str, Any]: ...

    def list_artifact_types(self, pipeline: str | None, stage: str | None) -> dict[str, Any]: ...

    def list_artifacts(
        self,
        *,
        pipeline: str | None,
        stage: str | None,
        artifact_type: str | None,
        limit: int,
    ) -> dict[str, Any]: ...

    def execution_lineage(self, pipeline: str | None, execution_id: str) -> dict[str, Any]: ...

    def artifact_lineage(self, pipeline: str | None, artifact_id: str) -> dict[str, Any]: ...

    def model_card(self, model_id: str) -> dict[str, Any]: ...

    def find_correlation(self, correlation_id: str, limit: int) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...
