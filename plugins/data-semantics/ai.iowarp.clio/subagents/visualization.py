"""Visualization Planning Expert: a defined subagent of data-semantics."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="Visualization Planning Expert",
    plugins=["plot"],
    tools=["plot_histogram_plot", "plot_line_plot", "load_skill"],
)
