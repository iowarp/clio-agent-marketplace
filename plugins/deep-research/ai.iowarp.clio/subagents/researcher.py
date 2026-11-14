"""Web Evidence Researcher: a defined subagent of deep-research."""

from clio_agent.sdk import PromptFile, Subagent

researcher = Subagent(
    "researcher",
    prompt=PromptFile("prompt/subagents/researcher.md"),
    description="Repeatable direct leaf that investigates one research direction with web search and fetch and scholarly literature search and lookup, returning a compact fact-versus-inference evidence packet (each finding with its fetched URL and supporting quote) and an auditable search/fetch log.",
    plugins=["web", "literature"],
    tools=["web_search", "web_fetch", "literature_search", "literature_lookup"],
    max_iters=32,
    # Its findings travel to the critic typed (workflow_state.packet.claims).
    structured_outputs={"workflow_state": True},
)
