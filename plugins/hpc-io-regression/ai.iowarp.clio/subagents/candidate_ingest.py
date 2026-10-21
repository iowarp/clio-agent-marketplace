"""Candidate Trace Ingest Worker: a defined subagent of hpc-io-regression."""

from clio_agent.sdk import PromptFile, Subagent

candidate_ingest = Subagent(
    "candidate_ingest",
    prompt=PromptFile("prompt/subagents/candidate_ingest.md"),
    description="Candidate Trace Ingest Worker: hpc candidate trace ingest",
    plugins=[],
    tools=["load_skill"],
)
