"""Research Evidence Critic: a defined subagent of deep-research."""

from clio_agent.sdk import PromptFile, Subagent

critic = Subagent(
    "critic",
    prompt=PromptFile("prompt/subagents/critic.md"),
    description="Repeatable direct leaf that independently verifies researchers' evidence packets with its own web search and fetch, and returns a typed audit in workflow_state.audit: verified claims (claim, fetched source URL, supporting quote), rejected claims with reasons, and the material gaps that remain.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    # The deep-research flow branches on the typed audit; it validates the shape.
    structured_outputs={"workflow_state": True},
)
