"""GNSS Visualization Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="Renders a PNG plot from the staged station CSV(s) via a plotting tool. Produces the artifact (PNG) path. Needs a staged CSV + profile.",
    plugins=["pandas", "plot"],
    tools=["pandas_profile_csv", "plot_plot_timeseries"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
