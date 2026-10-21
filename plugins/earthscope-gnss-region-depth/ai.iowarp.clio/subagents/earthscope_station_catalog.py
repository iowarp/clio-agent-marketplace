"""EarthScope Station Catalog Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

earthscope_station_catalog = Subagent(
    "earthscope_station_catalog",
    prompt=PromptFile("prompt/subagents/earthscope_station_catalog.md"),
    description="EarthScope Station Catalog Expert",
    plugins=["ndp", "delegation"],
    tools=[
        "ndp_filter_earthscope_station_catalog",
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
