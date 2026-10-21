"""EarthScope NDP Data Expert: a defined subagent of earthscope-flat."""

from clio_agent.sdk import PromptFile, Subagent

ndp = Subagent(
    "ndp",
    prompt=PromptFile("prompt/subagents/ndp.md"),
    description="The single self-sufficient EarthScope DATA expert. For the resolved region it (1) discovers + stages + cleans the NDP EarthScope station-metadata catalog, (2) spatially filters it to the region and ranks nearby stations, (3) stages the selected station's real time-series CSV. Produces workflow_state.acquisition (staged CSV) OR an honest no-coverage blocker. Needs the resolved region from geospatial.",
    plugins=["ndp", "pandas", "geo"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource", "pandas_filter_data", "geo_filter_points_by_radius"],
    max_iters=40,
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
