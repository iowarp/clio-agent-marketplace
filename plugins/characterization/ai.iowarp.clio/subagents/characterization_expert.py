"""Characterization Expert: a defined subagent of characterization."""

from clio_agent.sdk import PromptFile, Subagent

characterization_expert = Subagent(
    "characterization_expert",
    prompt=PromptFile("prompt/subagents/characterization_expert.md"),
    description="Turns XCT, surface, microstructure, and fractographic measurements into quantified evidence about what a part actually is, not just what it was designed or built to be.",
    plugins=[],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
