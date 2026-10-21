"""Air Quality Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

air_quality = Subagent(
    "air_quality",
    prompt=PromptFile("prompt/subagents/air_quality.md"),
    description="Air Quality Expert: air quality",
    plugins=["ndp", "geo"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "geo_query_arcgis_features"],
    structured_outputs={"workflow_state": True},
)
