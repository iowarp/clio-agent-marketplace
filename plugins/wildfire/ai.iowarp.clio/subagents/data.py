"""Hazard Data Acquisition Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

data = Subagent(
    "data",
    prompt=PromptFile("prompt/subagents/data.md"),
    description="Hazard Data Acquisition Expert: hazard data acquisition",
    plugins=["delegation"],
    tools=[
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
    structured_outputs={
        "workflow_state": True,
        "evidence": True,
        "errors": True,
        "delegation": True,
    },
)
