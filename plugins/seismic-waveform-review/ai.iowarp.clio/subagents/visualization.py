"""Seismic Visualization Expert: a defined subagent of seismic-waveform-review."""

from clio_agent.sdk import PromptFile, Subagent

visualization = Subagent(
    "visualization",
    prompt=PromptFile("prompt/subagents/visualization.md"),
    description="Seismic Visualization Expert: seismic visualization",
    plugins=[],
    tools=["load_skill"],
)
