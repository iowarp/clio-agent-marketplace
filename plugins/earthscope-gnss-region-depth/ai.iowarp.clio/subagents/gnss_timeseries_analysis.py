"""GNSS Time-Series Analysis Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

gnss_timeseries_analysis = Subagent(
    "gnss_timeseries_analysis",
    prompt=PromptFile("prompt/subagents/gnss_timeseries_analysis.md"),
    description="GNSS Time-Series Analysis Expert",
    plugins=["ndp", "delegation"],
    tools=["ndp_profile_csv_resource", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
