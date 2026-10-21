"""Seismic Event Context Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

seismic_event_catalog = Subagent(
    "seismic_event_catalog",
    prompt=PromptFile("prompt/subagents/seismic_event_catalog.md"),
    description="Looks up earthquake/event catalog context via tools — only when the user explicitly asks for events.",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
