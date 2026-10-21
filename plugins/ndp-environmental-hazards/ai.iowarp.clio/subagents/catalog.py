"""NDP Catalog Expert: a defined subagent of ndp-environmental-hazards."""

from clio_agent.sdk import PromptFile, Subagent

catalog = Subagent(
    "catalog",
    prompt=PromptFile("prompt/subagents/catalog.md"),
    description="NDP Catalog Expert",
    plugins=["ndp"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource"],
    structured_outputs={"evidence": True, "errors": True},
)
