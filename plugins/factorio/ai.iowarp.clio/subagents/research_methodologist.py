"""Research Methodologist: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

research_methodologist = Subagent(
    "research_methodologist",
    prompt=PromptFile("prompt/subagents/research_methodologist.md"),
    description="Tests research-question quality, hypotheses, scope, novelty burden, and study logic.",
    plugins=[],
    tools=["ask_user"],
    max_iters=40,
    structured_outputs={"workflow_state": False},
)
