"""Visualization Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="Visualization Expert: hazard map",
    plugins=["geo"],
    tools=["geo_render_feature_map"],
    structured_outputs={"workflow_state": True, "errors": True},
)
