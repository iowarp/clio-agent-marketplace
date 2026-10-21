"""Mass Spectrometry Expert: a defined subagent of proteomics-mzml-review."""

from clio_agent.sdk import PromptFile, Subagent

mass_spec = Subagent(
    "mass_spec",
    prompt=PromptFile("prompt/subagents/mass_spec.md"),
    description="Mass Spectrometry Expert: mass spectrometry",
    plugins=["delegation"],
    tools=[
        "load_skill",
        "spawn_agent_task",
        "spawn_agents_parallel",
        "wait_tasks",
        "observe_tasks",
        "get_task_result",
    ],
)
