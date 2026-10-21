"""Fatigue and Failure Expert: a defined subagent of fatigue."""

from clio_agent.sdk import PromptFile, Subagent

fatigue_failure_expert = Subagent(
    "fatigue_failure_expert",
    prompt=PromptFile("prompt/subagents/fatigue_failure_expert.md"),
    description="Predicts fatigue life and reasons about failure mechanisms by consuming outputs from simulation, materials, characterization, and testing rather than treating fatigue as a single-discipline calculation.",
    plugins=[],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
