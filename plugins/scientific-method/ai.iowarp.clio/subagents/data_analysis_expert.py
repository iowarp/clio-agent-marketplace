"""Data Analysis Expert: a defined subagent of scientific-method."""

from clio_agent.sdk import PromptFile, Subagent

data_analysis_expert = Subagent(
    "data_analysis_expert",
    prompt=PromptFile("prompt/subagents/data_analysis_expert.md"),
    description="Turns raw results from testing, characterization, and simulation into defensible statistics, uncertainty bounds, and figures.",
    plugins=[],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
