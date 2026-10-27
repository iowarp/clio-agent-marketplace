"""Delegation on the task layer: spawning children and forking oneself."""

from clio_agent.sdk import native_tool

spawn_agent_task = native_tool("spawn_agent_task")
spawn_agents_parallel = native_tool("spawn_agents_parallel")
# Runs a skill whose frontmatter declares `effect: spawn_subagent_with_skill` in a child.
spawn_skill_task = native_tool("spawn_skill_task")
# A copy of the caller, conversation included, that runs beside it under the same parent.
fork = native_tool("fork")
