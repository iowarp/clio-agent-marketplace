"""Materials Scientist: a defined subagent of materials."""

from clio_agent.sdk import PromptFile, Subagent

materials_scientist = Subagent(
    "materials_scientist",
    prompt=PromptFile("prompt/subagents/materials_scientist.md"),
    description="Understands material behavior and connects processing to structure, properties, and performance for a specific material system.",
    plugins=[],
    tools=["ask_user", "load_skill"],
    max_iters=64,
    structured_outputs={"workflow_state": False},
)
