"""Geospatial Resolution Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

geospatial = Subagent(
    "geospatial",
    prompt=PromptFile("prompt/subagents/geospatial.md"),
    description="Geospatial Resolution Expert",
    plugins=["delegation"],
    tools=["spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
