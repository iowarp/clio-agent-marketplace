"""Evidence critic: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_critic = Subagent(
    "evidence_critic",
    prompt=PromptFile("prompt/subagents/evidence_critic.md"),
    description=(
        "Independently challenges evidence_researcher's draft synthesis with fresh source "
        "checks. Started by evidence_researcher, not directly."
    ),
    plugins=["web", "workspace"],
    tools=[
        "web_search",
        "web_fetch",
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "view_image",
    ],
    max_iters=32,
)
