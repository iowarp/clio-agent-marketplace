"""Simulation Readiness Expert: a defined subagent of materials-crystal-review."""

from clio_agent.sdk import PromptFile, Subagent

simulation_readiness = Subagent(
    "simulation_readiness",
    prompt=PromptFile("prompt/subagents/simulation_readiness.md"),
    description="Simulation Readiness Expert: materials simulation readiness",
    plugins=[],
    tools=["load_skill"],
)
