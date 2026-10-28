"""Evidence leaf: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_leaf = Subagent(
    "evidence_leaf",
    prompt=PromptFile("prompt/subagents/evidence_leaf.md"),
    description=(
        "One bounded web-evidence lane for evidence_researcher, with fetched-source "
        "provenance. Started by evidence_researcher, not directly."
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
