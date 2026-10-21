"""NDP Catalog Child Expert: a defined subagent of seismic-waveform-review."""

from clio_agent.sdk import PromptFile, Subagent

ndp_catalog = Subagent(
    "ndp_catalog",
    prompt=PromptFile("prompt/subagents/ndp_catalog.md"),
    description="NDP Catalog Child Expert: ndp catalog",
    plugins=["ndp"],
    tools=["ndp_list_organizations", "ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource", "load_skill"],
)
