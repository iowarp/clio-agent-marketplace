"""GNSS Time-Series Analysis Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

gnss_timeseries_analysis = Subagent(
    "gnss_timeseries_analysis",
    prompt=PromptFile("prompt/subagents/gnss_timeseries_analysis.md"),
    description="GNSS Time-Series Analysis Expert",
    plugins=["ndp"],
    tools=["ndp_profile_csv_resource"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
