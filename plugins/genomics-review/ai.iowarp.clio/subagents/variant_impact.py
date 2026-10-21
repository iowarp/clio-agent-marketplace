"""Variant Impact Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

variant_impact = Subagent(
    "variant_impact",
    prompt=PromptFile("prompt/subagents/variant_impact.md"),
    description="Variant Impact Expert: genomics variant impact",
    plugins=[],
    tools=["load_skill"],
)
