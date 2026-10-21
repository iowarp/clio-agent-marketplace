"""Manufacturing Expert: a defined subagent of am-process."""

from clio_agent.sdk import PromptFile, Subagent

manufacturing_expert = Subagent(
    "manufacturing_expert",
    prompt=PromptFile("prompt/subagents/manufacturing_expert.md"),
    description="Understands how a proposed design actually becomes a physical component, and what the manufacturing route does to the part along the way.",
    plugins=["materials"],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
