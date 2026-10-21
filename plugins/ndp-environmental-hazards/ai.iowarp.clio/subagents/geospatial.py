"""NDP Geospatial Hazard Expert: a defined subagent of ndp-environmental-hazards."""

from clio_agent.sdk import PromptFile, Subagent

geospatial = Subagent(
    "geospatial",
    prompt=PromptFile("prompt/subagents/geospatial.md"),
    description="NDP Geospatial Hazard Expert",
    plugins=["ndp"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_query_arcgis_features"],
    structured_outputs={"evidence": True, "errors": True},
)
