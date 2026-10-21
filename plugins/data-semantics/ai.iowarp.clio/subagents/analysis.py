"""Semantic Analysis Expert: a defined subagent of data-semantics."""

from clio_agent.sdk import PromptFile, Subagent

analysis = Subagent(
    "analysis",
    prompt=PromptFile("prompt/subagents/analysis.md"),
    description="Semantic Analysis Expert",
    plugins=["pandas", "parquet"],
    tools=["pandas_statistical_summary", "parquet_aggregate_column_tool", "load_skill"],
)
