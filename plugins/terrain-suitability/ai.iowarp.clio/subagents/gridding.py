"""Point-Cloud Gridding Worker: a defined subagent of terrain-suitability."""

from clio_agent.sdk import PromptFile, Subagent

gridding = Subagent(
    "gridding",
    prompt=PromptFile("prompt/subagents/gridding.md"),
    description="Point-Cloud Gridding Worker: terrain pointcloud gridding",
    plugins=[],
    tools=["load_skill"],
)
