"""NDP Terrain Data Collector: a defined subagent of terrain-suitability."""

from clio_agent.sdk import PromptFile, Subagent

ndp_collector = Subagent(
    "ndp_collector",
    prompt=PromptFile("prompt/subagents/ndp_collector.md"),
    description="NDP Terrain Data Collector: terrain ndp collection",
    plugins=["ndp"],
    tools=["ndp_list_organizations", "ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource", "load_skill"],
)
