"""SAC Format Child Expert: a defined subagent of seismic-waveform-review."""

from clio_agent.sdk import PromptFile, Subagent

sac_format = Subagent(
    "sac_format",
    prompt=PromptFile("prompt/subagents/sac_format.md"),
    description="SAC Format Child Expert: sac waveform format",
    plugins=[],
    tools=["load_skill"],
)
