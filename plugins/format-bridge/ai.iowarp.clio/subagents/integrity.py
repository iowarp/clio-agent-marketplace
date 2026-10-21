"""Integrity Review Expert: a defined subagent of format-bridge."""

from clio_agent.sdk import PromptFile, Subagent

integrity = Subagent(
    "integrity",
    prompt=PromptFile("prompt/subagents/integrity.md"),
    description="Integrity Review Expert: scientific conversion integrity",
    plugins=["parquet"],
    tools=["parquet_analyze_schema", "parquet_compute_statistics", "load_skill"],
)
