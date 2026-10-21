"""Abaqus and Tosca Engineer: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

abaqus_engineer = Subagent(
    "abaqus_engineer",
    prompt=PromptFile("prompt/subagents/abaqus_engineer.md"),
    description="Turns an approved formulation into complete reviewable Abaqus Python and required Tosca artifacts without claiming execution.",
    plugins=["abaqus", "topology"],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
