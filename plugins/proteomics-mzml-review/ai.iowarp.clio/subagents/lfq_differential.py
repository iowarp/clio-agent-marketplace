"""LFQ Differential Abundance Expert: a defined subagent of proteomics-mzml-review."""

from clio_agent.sdk import PromptFile, Subagent

lfq_differential = Subagent(
    "lfq_differential",
    prompt=PromptFile("prompt/subagents/lfq_differential.md"),
    description="LFQ Differential Abundance Expert: proteomics lfq differential abundance",
    plugins=[],
    tools=["load_skill"],
)
