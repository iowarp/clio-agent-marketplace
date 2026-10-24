"""Construct Spotter query providers from one resolved CLIO configuration."""

from __future__ import annotations

from spotter_ai.config import SpotterConfig
from spotter_ai.providers.cmf import CMFProvider
from spotter_ai.providers.flowcept import FlowceptProvider
from spotter_ai.providers.jsonl import JsonlProvider
from spotter_ai.providers.protocol import AgenticProvider, ArtifactProvider


def create_providers(config: SpotterConfig) -> tuple[AgenticProvider, ArtifactProvider]:
    """Create the configured agentic and artifact query providers."""
    native: JsonlProvider | None = None
    if config.native is not None:
        native = JsonlProvider(config.native)

    if config.agentic_provider == "flowcept":
        if config.flowcept is None:
            raise ValueError("resolved Flowcept configuration is missing")
        agentic: AgenticProvider = FlowceptProvider(config.flowcept)
    elif native is not None:
        agentic = native
    else:
        raise ValueError("resolved native agentic configuration is missing")

    if config.artifact_provider == "cmf":
        if config.cmf is None:
            raise ValueError("resolved CMF configuration is missing")
        artifact: ArtifactProvider = CMFProvider(config.cmf)
    elif native is not None:
        artifact = native
    else:
        raise ValueError("resolved native artifact configuration is missing")

    return agentic, artifact
