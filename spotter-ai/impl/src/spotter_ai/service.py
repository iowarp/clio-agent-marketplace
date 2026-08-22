"""Provider-selecting service behind Spotter's purpose-specific MCP tools."""

from __future__ import annotations

from typing import Any

from spotter_ai.errors import capability_unavailable
from spotter_ai.providers.protocol import AgenticProvider, ArtifactProvider


class ProvenanceService:
    """Route each query to the configured provider for its provenance domain."""

    def __init__(self, agentic: AgenticProvider, artifact: ArtifactProvider) -> None:
        self.agentic = agentic
        self.artifact = artifact

    def capabilities(self) -> dict[str, Any]:
        """Describe active providers, health, and exact supported operations."""
        return {
            "agentic": {
                "provider": self.agentic.name,
                "capabilities": sorted(self.agentic.capabilities()),
                "health": self.agentic.health(),
            },
            "artifact": {
                "provider": self.artifact.name,
                "capabilities": sorted(self.artifact.capabilities()),
                "health": self.artifact.health(),
            },
        }

    def require_agentic(self, operation: str) -> AgenticProvider:
        """Return the agentic provider when it implements ``operation``."""
        if operation not in self.agentic.capabilities():
            raise capability_unavailable(operation, self.agentic.name)
        return self.agentic

    def require_artifact(self, operation: str) -> ArtifactProvider:
        """Return the artifact provider when it implements ``operation``."""
        if operation not in self.artifact.capabilities():
            raise capability_unavailable(operation, self.artifact.name)
        return self.artifact

    def trace_correlation(self, correlation_id: str, limit: int) -> dict[str, Any]:
        """Join agentic and artifact evidence on an explicit producer correlation id."""
        agentic = self.require_agentic("trace_correlation")
        artifact = self.require_artifact("trace_correlation")
        agentic_matches = agentic.find_correlation(correlation_id, limit)
        artifact_matches = (
            agentic_matches
            if artifact is agentic
            else artifact.find_correlation(correlation_id, limit)
        )
        return {
            "correlation_id": correlation_id,
            "agentic": {
                "provider": agentic.name,
                "items": agentic_matches,
                "count": len(agentic_matches),
            },
            "artifact": {
                "provider": artifact.name,
                "items": artifact_matches,
                "count": len(artifact_matches),
            },
        }

    def close(self) -> None:
        """Close each distinct provider exactly once."""
        self.agentic.close()
        if self.artifact is not self.agentic:
            self.artifact.close()
