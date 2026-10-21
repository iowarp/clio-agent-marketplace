"""EarthScope Station Catalog Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

earthscope_station_catalog = Subagent(
    "earthscope_station_catalog",
    prompt=PromptFile("prompt/subagents/earthscope_station_catalog.md"),
    description="Spatially filters the staged metadata catalog to the resolved region (geo_filter tool) and ranks nearby stations. Produces station_catalog ranking (or no_candidates). Needs acquisition.metadata_path from discovery.",
    plugins=["shell", "geo"],
    tools=["shell_bash", "geo_filter_points_by_radius"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
