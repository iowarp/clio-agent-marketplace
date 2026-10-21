"""Simulation Methodologist: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

simulation_methodologist = Subagent(
    "simulation_methodologist",
    prompt=PromptFile("prompt/subagents/simulation_methodologist.md"),
    description="Converts the research claim into a physically defensible simulation formulation and validation plan.",
    plugins=["visuals", "abaqus", "topology"],
    tools=["ask_user", "create_a2ui_surface", "load_skill"],
    max_iters=48,
    structured_outputs={"workflow_state": False},
)
