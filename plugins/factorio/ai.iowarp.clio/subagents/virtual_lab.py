"""Virtual lab and feasibility expert: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

virtual_lab = Subagent(
    "virtual_lab",
    prompt=PromptFile("prompt/subagents/virtual_lab.md"),
    description=(
        "Maps what the scientist can actually execute (equipment, software and licences, "
        "compute and scheduler, data, access, people, schedule) to the candidate methods, "
        "checking installed software and clusters itself where it can."
    ),
    plugins=["workspace", "shell", "visuals"],
    tools=[
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "view_image",
        "shell_bash",
        "create_a2ui_surface",
        "update_a2ui_components",
        "update_a2ui_data_model",
        "inspect_a2ui_surface",
        "capture_a2ui_surface",
    ],
    max_iters=40,
)
