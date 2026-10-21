"""Seismic Event Context Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

seismic_event_catalog = Subagent(
    "seismic_event_catalog",
    prompt=PromptFile("prompt/subagents/seismic_event_catalog.md"),
    description="Seismic Event Context Expert",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
