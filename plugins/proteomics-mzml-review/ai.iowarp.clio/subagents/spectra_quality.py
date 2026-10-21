"""Spectra Quality Expert: a defined subagent of proteomics-mzml-review."""

from clio_agent.sdk import PromptFile, Subagent

spectra_quality = Subagent(
    "spectra_quality",
    prompt=PromptFile("prompt/subagents/spectra_quality.md"),
    description="Spectra Quality Expert: proteomics spectra quality",
    plugins=[],
    tools=["load_skill"],
)
