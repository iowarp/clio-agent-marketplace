"""Independent Scientific and Simulation Reviewer: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

independent_reviewer = Subagent(
    "independent_reviewer",
    prompt=PromptFile("prompt/subagents/independent_reviewer.md"),
    description="Adversarially reviews the research logic, evidence, physical formulation, generated package, and verification claims.",
    plugins=[],
    tools=[],
    max_iters=48,
    structured_outputs={"workflow_state": False},
)
