"""General subagent spawning on the task layer."""

from clio_agent.sdk import native_tool

spawn_agent_task = native_tool("spawn_agent_task")
spawn_agents_parallel = native_tool("spawn_agents_parallel")
