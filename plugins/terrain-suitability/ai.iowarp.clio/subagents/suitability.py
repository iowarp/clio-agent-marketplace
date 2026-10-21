"""Site Suitability Expert: a defined subagent of terrain-suitability."""

from clio_agent.sdk import PromptFile, Subagent

suitability = Subagent(
    "suitability",
    prompt=PromptFile("prompt/subagents/suitability.md"),
    description="Site Suitability Expert: terrain site suitability",
    plugins=[],
    tools=["load_skill"],
)
