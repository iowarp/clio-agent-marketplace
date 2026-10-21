"""Scientific Evidence Critic: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

evidence_critic = Subagent(
    "evidence_critic",
    prompt=PromptFile("prompt/subagents/evidence_critic.md"),
    description="Independently challenges a proposed evidence dossier, verifies important citations through fresh fetches/searches, and identifies unsupported claims, missing counterevidence, or required follow-up research.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    structured_outputs={"evidence": True, "errors": True},
)
