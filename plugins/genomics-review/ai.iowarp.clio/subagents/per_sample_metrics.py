"""Per-Sample Metrics Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

per_sample_metrics = Subagent(
    "per_sample_metrics",
    prompt=PromptFile("prompt/subagents/per_sample_metrics.md"),
    description="Per-Sample Metrics Expert: genomics per sample metrics",
    plugins=[],
    tools=["load_skill"],
)
