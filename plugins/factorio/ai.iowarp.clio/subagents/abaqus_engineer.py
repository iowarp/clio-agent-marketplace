"""Abaqus and Tosca Engineer: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

abaqus_engineer = Subagent(
    "abaqus_engineer",
    prompt=PromptFile("prompt/subagents/abaqus_engineer.md"),
    description="Turns a scientist-approved simulation specification into complete, reviewable Abaqus Python and any required Tosca parameter artifact without claiming unperformed execution.",
    plugins=[],
    tools=[],
    max_iters=64,
    structured_outputs={"evidence": True, "errors": True},
)
