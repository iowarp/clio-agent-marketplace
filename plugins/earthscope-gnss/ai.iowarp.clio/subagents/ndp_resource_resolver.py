"""NDP Resource Resolver Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

ndp_resource_resolver = Subagent(
    "ndp_resource_resolver",
    prompt=PromptFile("prompt/subagents/ndp_resource_resolver.md"),
    description="Stages the selected station's time-series CSV via NDP tools. Produces acquisition.status=staged + local_path. Needs a ranked station from the catalog.",
    plugins=["ndp"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource"],
    max_iters=36,
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
