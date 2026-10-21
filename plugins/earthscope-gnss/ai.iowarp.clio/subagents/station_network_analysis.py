"""Station Network Analysis Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

station_network_analysis = Subagent(
    "station_network_analysis",
    prompt=PromptFile("prompt/subagents/station_network_analysis.md"),
    description="Assesses station/network suitability from the staged evidence via tools.",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
