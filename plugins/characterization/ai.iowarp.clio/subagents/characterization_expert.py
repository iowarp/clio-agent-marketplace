"""Characterization expert: a defined subagent of characterization."""

from clio_agent.sdk import PromptFile, Subagent

characterization_expert = Subagent(
    "characterization_expert",
    prompt=PromptFile("prompt/subagents/characterization_expert.md"),
    description=(
        "Turns XCT, surface, microstructure and fractographic measurements into quantified "
        "evidence about what a part actually is, analysing the scientist's images and data "
        "files itself. Use for defect, porosity, roughness, microstructure and failure-surface "
        "questions."
    ),
    plugins=["workspace", "shell", "manufacturing", "scientific-method"],
    tools=[
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "fs_write_file",
        "fs_edit_file",
        "view_image",
        "shell_bash",
        "prepare_execution_runtime",
    ],
    max_iters=64,
)
