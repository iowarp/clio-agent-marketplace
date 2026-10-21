"""NDP EarthScope Dataset Discovery Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

ndp_dataset_discovery = Subagent(
    "ndp_dataset_discovery",
    prompt=PromptFile("prompt/subagents/ndp_dataset_discovery.md"),
    description="NDP EarthScope Dataset Discovery Expert",
    plugins=["ndp", "delegation"],
    tools=["ndp_search_datasets", "ndp_get_dataset_details", "ndp_stage_resource", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
