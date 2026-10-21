"""Station Network Analysis Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

station_network_analysis = Subagent(
    "station_network_analysis",
    prompt=PromptFile("prompt/subagents/station_network_analysis.md"),
    description="Station Network Analysis Expert",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
