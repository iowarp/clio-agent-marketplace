"""Terrain Derivation Expert: a defined subagent of terrain-suitability."""

from clio_agent.sdk import PromptFile, Subagent

terrain_derivation = Subagent(
    "terrain_derivation",
    prompt=PromptFile("prompt/subagents/terrain_derivation.md"),
    description="Terrain Derivation Expert: terrain derivation",
    plugins=["delegation"],
    tools=["load_skill", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
)
