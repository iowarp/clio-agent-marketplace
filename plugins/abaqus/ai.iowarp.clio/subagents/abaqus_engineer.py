"""Abaqus engineer: a defined subagent of the abaqus plugin."""

from clio_agent.sdk import PromptFile, Subagent

abaqus_engineer = Subagent(
    "abaqus_engineer",
    prompt=PromptFile("prompt/subagents/abaqus_engineer.md"),
    description=(
        "Turns an approved simulation formulation into a complete Abaqus (and, when asked, "
        "Tosca) package, runs it when Abaqus is reachable, and reports exactly what was "
        "generated, executed and checked. Use for Abaqus scripts, input decks, jobs and "
        "result extraction."
    ),
    plugins=["workspace", "shell", "fea-methods", "manufacturing-processes", "slurm"],
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
