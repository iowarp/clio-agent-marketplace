"""EarthScope Data Acquisition Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

data = Subagent(
    "data",
    prompt=PromptFile("prompt/subagents/data.md"),
    description="Discovers EarthScope/NDP GNSS station resources for the RESOLVED region and stages a real station time-series CSV via NDP tools (it orchestrates discovery -> spatial ranking -> staging). Produces workflow_state.acquisition (a staged CSV path) OR an honest no-coverage blocker. Needs the resolved region from geospatial.",
    plugins=["delegation"],
    tools=[
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
    structured_outputs={
        "workflow_state": True,
        "evidence": True,
        "errors": True,
        "delegation": True,
    },
)
