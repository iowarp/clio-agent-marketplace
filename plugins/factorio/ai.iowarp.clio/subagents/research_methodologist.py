"""Research Methodologist: a defined subagent of factorio."""

from clio_agent.sdk import PromptFile, Subagent

research_methodologist = Subagent(
    "research_methodologist",
    prompt=PromptFile("prompt/subagents/research_methodologist.md"),
    description="Durable consultation for turning an idea into a specific, answerable research question with explicit hypotheses, scope, novelty burden, and decision points.",
    plugins=[],
    tools=[],
    max_iters=40,
    structured_outputs={"evidence": True, "errors": True},
)
