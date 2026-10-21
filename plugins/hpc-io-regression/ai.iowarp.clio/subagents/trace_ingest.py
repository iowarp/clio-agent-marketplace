"""Trace Ingest Expert: a defined subagent of hpc-io-regression."""

from clio_agent.sdk import PromptFile, Subagent

trace_ingest = Subagent(
    "trace_ingest",
    prompt=PromptFile("prompt/subagents/trace_ingest.md"),
    description="Trace Ingest Expert: hpc trace ingest",
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
