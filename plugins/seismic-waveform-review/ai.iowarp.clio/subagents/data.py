"""Seismic Data Expert: a defined subagent of seismic-waveform-review."""

from clio_agent.sdk import PromptFile, Subagent

data = Subagent(
    "data",
    prompt=PromptFile("prompt/subagents/data.md"),
    description="Seismic Data Expert: seismic data access",
    plugins=["delegation"],
    tools=[
        "load_skill",
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
)
