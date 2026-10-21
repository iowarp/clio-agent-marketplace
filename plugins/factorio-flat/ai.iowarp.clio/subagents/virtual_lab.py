"""Virtual Lab and Feasibility Expert: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

virtual_lab = Subagent(
    "virtual_lab",
    prompt=PromptFile("prompt/subagents/virtual_lab.md"),
    description="Maps experimental, software, compute, data, access, and collaboration resources to the current methods.",
    plugins=["visuals"],
    tools=["ask_user", "create_a2ui_surface"],
    max_iters=40,
    structured_outputs={"workflow_state": False},
)
