"""Peptide Search Readiness Expert: a defined subagent of proteomics-mzml-review."""

from clio_agent.sdk import PromptFile, Subagent

search_readiness = Subagent(
    "search_readiness",
    prompt=PromptFile("prompt/subagents/search_readiness.md"),
    description="Peptide Search Readiness Expert: proteomics search readiness",
    plugins=[],
    tools=["load_skill"],
)
