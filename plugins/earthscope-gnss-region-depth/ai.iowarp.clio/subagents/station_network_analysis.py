"""Station Network Analysis Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

station_network_analysis = Subagent(
    "station_network_analysis",
    prompt=PromptFile("prompt/subagents/station_network_analysis.md"),
    description="Station Network Analysis Expert",
    plugins=["delegation"],
    tools=["spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
