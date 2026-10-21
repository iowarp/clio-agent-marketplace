"""NDP EarthScope Dataset Discovery Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

ndp_dataset_discovery = Subagent(
    "ndp_dataset_discovery",
    prompt=PromptFile("prompt/subagents/ndp_dataset_discovery.md"),
    description="NDP EarthScope Dataset Discovery Expert",
    plugins=["ndp"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
