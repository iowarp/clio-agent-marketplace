"""Geospatial Resolution Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

geospatial = Subagent(
    "geospatial",
    prompt=PromptFile("prompt/subagents/geospatial.md"),
    description="Geospatial Resolution Expert",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
