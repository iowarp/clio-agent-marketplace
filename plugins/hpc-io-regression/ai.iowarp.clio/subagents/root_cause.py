"""HPC I/O Root Cause Expert: a defined subagent of hpc-io-regression."""

from clio_agent.sdk import PromptFile, Subagent

root_cause = Subagent(
    "root_cause",
    prompt=PromptFile("prompt/subagents/root_cause.md"),
    description="HPC I/O Root Cause Expert: hpc io root cause",
    plugins=[],
    tools=["load_skill"],
)
