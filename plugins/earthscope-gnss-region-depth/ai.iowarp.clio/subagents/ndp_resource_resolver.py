"""NDP Resource Resolver Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

ndp_resource_resolver = Subagent(
    "ndp_resource_resolver",
    prompt=PromptFile("prompt/subagents/ndp_resource_resolver.md"),
    description="NDP Resource Resolver Expert",
    plugins=["ndp", "delegation"],
    tools=[
        "ndp_search_datasets",
        "ndp_get_dataset_details",
        "ndp_stage_resource",
        "ndp_filter_earthscope_station_catalog",
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
