"""Lossy Dtype Policy Worker: a defined subagent of format-bridge."""

from clio_agent.sdk import PromptFile, Subagent

lossy_policy = Subagent(
    "lossy_policy",
    prompt=PromptFile("prompt/subagents/lossy_policy.md"),
    description="Lossy Dtype Policy Worker: lossy dtype policy review",
    plugins=[],
    tools=["load_skill"],
)
