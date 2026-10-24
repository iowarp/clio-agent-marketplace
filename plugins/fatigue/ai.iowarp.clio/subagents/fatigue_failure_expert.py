"""Fatigue and failure expert: a defined subagent of fatigue."""

from clio_agent.sdk import PromptFile, Subagent

fatigue_failure_expert = Subagent(
    "fatigue_failure_expert",
    prompt=PromptFile("prompt/subagents/fatigue_failure_expert.md"),
    description=(
        "Predicts fatigue life and reasons about failure mechanisms by combining simulation "
        "stresses, material properties, measured defects and test data, and runs the life "
        "calculations itself. Use for fatigue life, crack initiation, fracture and failure "
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
