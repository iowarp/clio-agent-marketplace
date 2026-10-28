"""Web Evidence Researcher: a defined subagent of deep-research."""

from clio_agent.sdk import PromptFile, Subagent

researcher = Subagent(
    "researcher",
    prompt=PromptFile("prompt/subagents/researcher.md"),
    description="Repeatable direct leaf that investigates one research direction with configured web search and fetch tools, returning a compact fact-versus-inference evidence packet (each finding with its fetched URL and supporting quote) and an auditable search/fetch log.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
)
