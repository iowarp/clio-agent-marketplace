"""Research Evidence Critic: a defined subagent of deep-research."""

from clio_agent.sdk import PromptFile, Subagent

critic = Subagent(
    "critic",
    prompt=PromptFile("prompt/subagents/critic.md"),
    description="Repeatable direct leaf that independently verifies one researcher's evidence packet (claims bound to the pages it fetched, with the text around each quote), fetching itself where needed, and returns a typed audit in workflow_state.audit: verified claims (claim, fetched source, supporting quote), rejected claims with reasons, and the open questions its direction leaves.",
    plugins=["web", "literature"],
    tools=["web_search", "web_fetch", "literature_lookup"],
    max_iters=32,
    # The deep-research flow branches on the typed audit; it validates the shape.
    structured_outputs={"workflow_state": True},
)
