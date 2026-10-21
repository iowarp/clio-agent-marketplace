"""Scientific Web Evidence Leaf: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_leaf = Subagent(
    "evidence_leaf",
    prompt=PromptFile("prompt/subagents/evidence_leaf.md"),
    description="Repeatable web-enabled leaf that investigates one bounded scientific evidence lane and returns fetched-source findings plus exact search/fetch provenance.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    structured_outputs={"evidence": True, "errors": True},
)
