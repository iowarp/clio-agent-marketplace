"""EarthScope Scientific Analysis Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

analysis = Subagent(
    "analysis",
    prompt=PromptFile("prompt/subagents/analysis.md"),
    description="EarthScope Scientific Analysis Expert",
    plugins=["delegation"],
    tools=["spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True, "delegation": True},
)
