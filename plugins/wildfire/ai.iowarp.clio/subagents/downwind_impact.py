"""Downwind Impact Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

downwind_impact = Subagent(
    "downwind_impact",
    prompt=PromptFile("prompt/subagents/downwind_impact.md"),
    description="Downwind Impact Expert: spatial overlap",
    plugins=["geo"],
    tools=["geo_points_in_polygons"],
    structured_outputs={"workflow_state": True, "evidence": True},
)
