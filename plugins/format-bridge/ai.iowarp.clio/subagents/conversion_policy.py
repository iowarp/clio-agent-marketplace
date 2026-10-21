"""Conversion Policy Expert: a defined subagent of format-bridge."""

from clio_agent.sdk import PromptFile, Subagent

conversion_policy = Subagent(
    "conversion_policy",
    prompt=PromptFile("prompt/subagents/conversion_policy.md"),
    description="Conversion Policy Expert: scientific format conversion policy",
    plugins=["delegation"],
    tools=["load_skill", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
)
