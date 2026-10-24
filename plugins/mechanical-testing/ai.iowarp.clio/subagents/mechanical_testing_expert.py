"""Mechanical testing expert: a defined subagent of mechanical-testing."""

from clio_agent.sdk import PromptFile, Subagent

mechanical_testing_expert = Subagent(
    "mechanical_testing_expert",
    prompt=PromptFile("prompt/subagents/mechanical_testing_expert.md"),
    description=(
        "Designs and interprets physical test campaigns (tensile and fatigue), reads the raw "
        "test data files itself, and connects simulation-predicted critical regions to what "
        "should actually be measured."
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
