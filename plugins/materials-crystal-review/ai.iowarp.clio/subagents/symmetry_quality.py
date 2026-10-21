"""Symmetry and Occupancy Expert: a defined subagent of materials-crystal-review."""

from clio_agent.sdk import PromptFile, Subagent

symmetry_quality = Subagent(
    "symmetry_quality",
    prompt=PromptFile("prompt/subagents/symmetry_quality.md"),
    description="Symmetry and Occupancy Expert: materials symmetry quality",
    plugins=[],
    tools=["load_skill"],
)
