"""Evidence researcher: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_researcher = Subagent(
    "evidence_researcher",
    prompt=PromptFile("prompt/subagents/evidence_researcher.md"),
    description=(
        "Answers one evidence question from the literature: runs its own evidence_leaf lanes "
        "and an independent evidence_critic, and returns a critic-reviewed, cited synthesis "
        "with a full source audit."
    ),
    plugins=["workspace", "scientific-method", "delegation"],
    tools=[
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "view_image",
        "spawn_agent_task",
        "spawn_agents_parallel",
    ],
    max_iters=72,
)
