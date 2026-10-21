"""NDP Artifact Visualization Expert: a defined subagent of ndp-environmental-hazards."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="NDP Artifact Visualization Expert",
    plugins=["ndp"],
    tools=["ndp_plot_csv_timeseries", "ndp_query_arcgis_features"],
    structured_outputs={"evidence": True, "errors": True},
)
