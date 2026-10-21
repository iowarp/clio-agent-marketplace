"""Variant Review Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

variants = Subagent(
    "variants",
    prompt=PromptFile("prompt/subagents/variants.md"),
    description="Variant Review Expert: genomics variants",
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
