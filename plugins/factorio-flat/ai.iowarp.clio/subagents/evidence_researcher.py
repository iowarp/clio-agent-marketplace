"""Scientific Evidence Coordinator: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

evidence_researcher = Subagent(
    "evidence_researcher",
    prompt=PromptFile("prompt/subagents/evidence_researcher.md"),
    description="Coordinates bounded evidence lanes and independent criticism into a source-grounded scientific dossier.",
    plugins=["scientific-method", "delegation"],
    tools=[
        "ask_user",
        "load_skill",
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
    max_iters=72,
    structured_outputs={"workflow_state": False},
)
