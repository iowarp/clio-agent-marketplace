"""Scientific Evidence Researcher: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_researcher = Subagent(
    "evidence_researcher",
    prompt=PromptFile("prompt/subagents/evidence_researcher.md"),
    description="Deep Researcher-style coordinator that dynamically fans out web evidence lanes, follows newly discovered branches, audits citations with an independent critic, and returns a source-grounded dossier to Factorio.",
    plugins=["delegation"],
    tools=["spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    max_iters=72,
    structured_outputs={"evidence": True, "errors": True, "delegation": True},
)
