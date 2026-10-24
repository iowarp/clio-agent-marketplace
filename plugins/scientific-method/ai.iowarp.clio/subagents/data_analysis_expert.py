"""Data analysis expert: a defined subagent of scientific-method."""

from clio_agent.sdk import PromptFile, Subagent

data_analysis_expert = Subagent(
    "data_analysis_expert",
    prompt=PromptFile("prompt/subagents/data_analysis_expert.md"),
    description=(
        "Turns raw results from experiments, measurements and simulations into defensible "
        "statistics, uncertainty bounds and figures, computing them itself with scripts kept "
        "in the workspace."
    ),
    plugins=["workspace", "shell"],
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
