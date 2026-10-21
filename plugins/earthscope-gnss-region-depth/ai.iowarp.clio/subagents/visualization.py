"""GNSS Visualization Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="GNSS Visualization Expert",
    plugins=["ndp", "delegation"],
    tools=["ndp_profile_csv_resource", "ndp_plot_csv_timeseries", "spawn_agent_task", "spawn_agents_parallel", "wait_tasks", "observe_tasks", "get_task_result"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
