"""Spatial Features Expert: a defined subagent of geospatial-field-review."""

from clio_agent.sdk import PromptFile, Subagent

spatial_features = Subagent(
    "spatial_features",
    prompt=PromptFile("prompt/subagents/spatial_features.md"),
    description="Spatial Features Expert: geospatial features",
    plugins=[],
    tools=["load_skill"],
)
