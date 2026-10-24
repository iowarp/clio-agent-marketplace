"""Research methodologist: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

research_methodologist = Subagent(
    "research_methodologist",
    prompt=PromptFile("prompt/subagents/research_methodologist.md"),
    description=(
        "Tests a research question's quality: hypotheses and rivals, scope, novelty burden, "
        "and whether the study logic can support the claim. Use for framing and study-design "
        "concerns."
    ),
    plugins=["workspace", "scientific-method"],
    tools=[
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "view_image",
    ],
    max_iters=40,
)
