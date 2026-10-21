"""NDP EarthScope Dataset Discovery Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

ndp_dataset_discovery = Subagent(
    "ndp_dataset_discovery",
    prompt=PromptFile("prompt/subagents/ndp_dataset_discovery.md"),
    description="Searches NDP and stages the EarthScope station-metadata catalog CSV via tools. Produces acquisition.metadata_path. Run FIRST in the data branch.",
    plugins=["ndp", "pandas"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource", "pandas_load_data", "pandas_filter_data"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
