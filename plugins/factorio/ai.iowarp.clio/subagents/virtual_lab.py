"""Virtual Lab and Feasibility Expert: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

virtual_lab = Subagent(
    "virtual_lab",
    prompt=PromptFile("prompt/subagents/virtual_lab.md"),
    description="Builds a targeted map of experimental equipment, software, licenses, compute, data, collaborators, access constraints, and realistic alternatives for the current research question.",
    plugins=[],
    tools=[],
    max_iters=40,
    structured_outputs={"evidence": True, "errors": True},
)
