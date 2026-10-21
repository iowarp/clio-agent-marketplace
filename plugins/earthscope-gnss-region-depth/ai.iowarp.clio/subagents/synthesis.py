"""EarthScope GNSS Synthesis Expert: a defined subagent of earthscope-gnss-region-depth."""

from clio_agent.sdk import PromptFile, Subagent

synthesis = Subagent(
    "synthesis",
    prompt=PromptFile("prompt/subagents/synthesis.md"),
    description="EarthScope GNSS Synthesis Expert",
    plugins=[],
    tools=[],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
