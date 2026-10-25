"""Simulation methodologist: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

simulation_methodologist = Subagent(
    "simulation_methodologist",
    prompt=PromptFile("prompt/subagents/simulation_methodologist.md"),
    description=(
        "Turns a research claim into a physically defensible, program-independent simulation "
        "formulation and validation plan: quantity of interest, idealization, materials, "
        "loads, mesh, optimization problem, sensitivities and benchmarks."
    ),
    plugins=["workspace", "shell", "visuals", "fea-methods", "manufacturing-processes"],
    tools=[
        "fs_read_file",
        "fs_list_directory",
        "fs_search_text",
        "fs_write_file",
        "fs_edit_file",
        "view_image",
        "shell_bash",
        "create_a2ui_surface",
        "update_a2ui_components",
        "update_a2ui_data_model",
        "inspect_a2ui_surface",
        "capture_a2ui_surface",
    ],
    max_iters=48,
)
