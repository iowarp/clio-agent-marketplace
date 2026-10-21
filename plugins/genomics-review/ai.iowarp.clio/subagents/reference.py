"""Reference Sequence Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

reference = Subagent(
    "reference",
    prompt=PromptFile("prompt/subagents/reference.md"),
    description="Reference Sequence Expert: genomics reference",
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
