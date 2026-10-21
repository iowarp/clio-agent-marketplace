"""Terrain Visual Summary Expert: a defined subagent of terrain-suitability."""

from clio_agent.sdk import PromptFile, Subagent

visual_summary = Subagent(
    "visual_summary",
    prompt=PromptFile("prompt/subagents/visual_summary.md"),
    description="Terrain Visual Summary Expert: terrain visual summary",
    plugins=["plot"],
    tools=["plot_bar_chart", "plot_summary", "load_skill"],
)
