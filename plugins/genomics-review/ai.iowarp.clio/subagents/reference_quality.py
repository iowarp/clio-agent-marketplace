"""Reference Quality Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

reference_quality = Subagent(
    "reference_quality",
    prompt=PromptFile("prompt/subagents/reference_quality.md"),
    description="Reference Quality Expert: genomics reference quality",
    plugins=[],
    tools=["load_skill"],
)
