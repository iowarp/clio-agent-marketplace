"""Scientific Web Evidence Leaf: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

evidence_leaf = Subagent(
    "evidence_leaf",
    prompt=PromptFile("prompt/subagents/evidence_leaf.md"),
    description="Investigates one bounded scientific evidence lane with fetched-source provenance.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    structured_outputs={"workflow_state": False},
)
