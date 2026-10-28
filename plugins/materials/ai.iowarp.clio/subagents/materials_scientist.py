"""Materials scientist: a defined subagent of materials."""

from clio_agent.sdk import PromptFile, Subagent

materials_scientist = Subagent(
    "materials_scientist",
    prompt=PromptFile("prompt/subagents/materials_scientist.md"),
    description=(
        "Explains why a material behaves as it does: processing history to microstructure "
        "to properties and service performance, for the specific material system and "
        "condition. Use for alloy behavior, heat treatment, microstructure and property "
        "questions."
    ),
    plugins=["workspace", "manufacturing", "scientific-method"],
    tools=["fs_read_file", "fs_list_directory", "fs_search_text", "view_image"],
    max_iters=64,
)
