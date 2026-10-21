"""Mechanical Testing Expert: a defined subagent of mechanical-testing."""

from clio_agent.sdk import PromptFile, Subagent

mechanical_testing_expert = Subagent(
    "mechanical_testing_expert",
    prompt=PromptFile("prompt/subagents/mechanical_testing_expert.md"),
    description="Designs and interprets physical mechanical test campaigns — tensile and fatigue — and connects predicted critical regions to what should actually be tested.",
    plugins=[],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
