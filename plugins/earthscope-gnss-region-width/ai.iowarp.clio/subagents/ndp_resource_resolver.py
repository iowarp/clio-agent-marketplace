"""NDP Resource Resolver Expert: a defined subagent of earthscope-gnss-region-width."""

from clio_agent.sdk import PromptFile, Subagent

ndp_resource_resolver = Subagent(
    "ndp_resource_resolver",
    prompt=PromptFile("prompt/subagents/ndp_resource_resolver.md"),
    description="NDP Resource Resolver Expert",
    plugins=["ndp"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
