"""EarthScope Station Catalog Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

earthscope_station_catalog = Subagent(
    "earthscope_station_catalog",
    prompt=PromptFile("prompt/subagents/earthscope_station_catalog.md"),
    description="EarthScope Station Catalog Expert",
    plugins=["ndp"],
    tools=["ndp_filter_earthscope_station_catalog"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
