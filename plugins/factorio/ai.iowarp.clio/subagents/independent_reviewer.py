"""Independent reviewer: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

independent_reviewer = Subagent(
    "independent_reviewer",
    prompt=PromptFile("prompt/subagents/independent_reviewer.md"),
    description=(
        "Adversarially reviews research logic, evidence, physical formulation, generated "
        "files and verification claims by reading and checking the actual files, before any "
        "package is called ready."
    ),
    plugins=[
        "workspace",
        "shell",
        "scientific-method",
        "fea-methods",
        "manufacturing-processes",
        "science-log",
    ],
    tools=[
        "fs_read_file",
        "query_log",
        "fs_list_directory",
        "fs_search_text",
        "view_image",
        "shell_bash",
    ],
    max_iters=48,
)
