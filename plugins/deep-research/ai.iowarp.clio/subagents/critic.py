"""Research Evidence Critic: a defined subagent of deep-research."""

from clio_agent.sdk import PromptFile, Subagent

critic = Subagent(
    "critic",
    prompt=PromptFile("prompt/subagents/critic.md"),
    description="Repeatable direct leaf that independently verifies an assembled evidence set and complete Markdown report draft, re-searches and re-fetches material claims, audits used-source citation coverage and the source ledger, and returns a pass-or-research-required verdict.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    structured_outputs={"evidence": True, "errors": True},
)
