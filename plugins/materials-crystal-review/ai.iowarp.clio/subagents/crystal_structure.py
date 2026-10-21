"""Crystal Structure Expert: a defined subagent of materials-crystal-review."""

from clio_agent.sdk import PromptFile, Subagent

crystal_structure = Subagent(
    "crystal_structure",
    prompt=PromptFile("prompt/subagents/crystal_structure.md"),
    description="Crystal Structure Expert: materials crystallography",
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
