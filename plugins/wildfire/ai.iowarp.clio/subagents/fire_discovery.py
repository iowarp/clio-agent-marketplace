"""Active Fire Discovery Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

fire_discovery = Subagent(
    "fire_discovery",
    prompt=PromptFile("prompt/subagents/fire_discovery.md"),
    description="fire_perimeters",
    plugins=["ndp", "geo"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "geo_query_arcgis_features"],
    structured_outputs={"workflow_state": True, "evidence": True},
)
