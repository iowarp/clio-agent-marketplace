"""GNSS Visualization Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="GNSS Visualization Expert",
    plugins=["ndp"],
    tools=["ndp_profile_csv_resource", "ndp_plot_csv_timeseries"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
