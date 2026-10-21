"""Cohort QC Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

cohort_qc = Subagent(
    "cohort_qc",
    prompt=PromptFile("prompt/subagents/cohort_qc.md"),
    description="Cohort QC Expert: genomics cohort qc",
    plugins=["delegation"],
    tools=["load_skill", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
)
