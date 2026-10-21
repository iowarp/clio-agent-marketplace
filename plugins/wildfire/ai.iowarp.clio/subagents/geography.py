"""Geography Expert: a defined subagent of wildfire."""

from clio_agent.sdk import PromptFile, Subagent

geography = Subagent(
    "geography",
    prompt=PromptFile("prompt/subagents/geography.md"),
    description="Geography Expert: region resolution",
    plugins=["geo"],
    tools=["geo_bounding_box"],
    structured_outputs={"workflow_state": True, "evidence": True},
)
