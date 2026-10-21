"""Visual Confirmation Expert: a defined subagent of format-bridge."""

from clio_agent.sdk import PromptFile, Subagent

visual_check = Subagent(
    "visual_check",
    prompt=PromptFile("prompt/subagents/visual_check.md"),
    description="Visual Confirmation Expert: scientific conversion visual confirmation",
    plugins=[],
    tools=["load_skill"],
)
