"""Manufacturing expert: a defined subagent of manufacturing-processes."""

from clio_agent.sdk import PromptFile, Subagent

manufacturing_expert = Subagent(
    "manufacturing_expert",
    prompt=PromptFile("prompt/subagents/manufacturing_expert.md"),
    description=(
        "Traces how a design becomes a physical part: process choice and parameters, build "
        "orientation, manufacturability, post-processing and finishing, and what each step "
        "does to the part. Use for any additive or conventional manufacturing route question."
    ),
    plugins=["workspace", "manufacturing", "scientific-method"],
    tools=["fs_read_file", "fs_list_directory", "fs_search_text", "view_image"],
    max_iters=64,
)
