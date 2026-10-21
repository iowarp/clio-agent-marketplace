"""Scientific Evidence Critic: a defined subagent of factorio-flat."""

from clio_agent.sdk import PromptFile, Subagent

evidence_critic = Subagent(
    "evidence_critic",
    prompt=PromptFile("prompt/subagents/evidence_critic.md"),
    description="Independently challenges a proposed evidence dossier and verifies its consequential claims and citations.",
    plugins=["web"],
    tools=["web_search", "web_fetch"],
    max_iters=32,
    structured_outputs={"workflow_state": False},
)
