"""Baseline Trace Ingest Worker: a defined subagent of hpc-io-regression."""

from clio_agent.sdk import PromptFile, Subagent

baseline_ingest = Subagent(
    "baseline_ingest",
    prompt=PromptFile("prompt/subagents/baseline_ingest.md"),
    description="Baseline Trace Ingest Worker: hpc baseline trace ingest",
    plugins=[],
    tools=["load_skill"],
)
