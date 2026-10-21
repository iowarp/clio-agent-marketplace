"""Simulation Methodologist: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

simulation_methodologist = Subagent(
    "simulation_methodologist",
    prompt=PromptFile("prompt/subagents/simulation_methodologist.md"),
    description="Converts the research question and evidence into a physically defensible simulation formulation, exposing assumptions, load paths, model-form choices, validation needs, and scientist-owned decisions.",
    plugins=[],
    tools=[],
    max_iters=48,
    structured_outputs={"evidence": True, "errors": True},
)
