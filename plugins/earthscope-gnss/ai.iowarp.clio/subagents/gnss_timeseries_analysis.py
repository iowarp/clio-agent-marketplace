"""GNSS Time-Series Analysis Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

gnss_timeseries_analysis = Subagent(
    "gnss_timeseries_analysis",
    prompt=PromptFile("prompt/subagents/gnss_timeseries_analysis.md"),
    description="Profiles the staged GNSS CSV time series (columns, ranges, uncertainty) via tools. Produces profile evidence.",
    plugins=["pandas"],
    tools=["pandas_profile_csv"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
