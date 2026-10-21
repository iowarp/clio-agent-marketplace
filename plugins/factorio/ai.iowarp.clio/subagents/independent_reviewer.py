"""Independent Scientific and Simulation Reviewer: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

independent_reviewer = Subagent(
    "independent_reviewer",
    prompt=PromptFile("prompt/subagents/independent_reviewer.md"),
    description="Adversarially reviews the research logic, evidence, physical formulation, Abaqus package, and claimed verification state before Factorio calls a handoff ready.",
    plugins=[],
    tools=[],
    max_iters=48,
    structured_outputs={"evidence": True, "errors": True},
)
