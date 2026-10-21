"""Smoke Forecast Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

smoke_forecast = Subagent(
    "smoke_forecast",
    prompt=PromptFile("prompt/subagents/smoke_forecast.md"),
    description="smoke_forecast",
    plugins=["ndp", "geo"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "geo_query_arcgis_features"],
    structured_outputs={"workflow_state": True},
)
