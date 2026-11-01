"""Generic roles every agent with delegation can start.

Each role runs the delegating agent's own plugins (``derive="caller"``), so a role
started by a manufacturing agent can read what that agent reads. All three are
read-only: tools that declare no side effects run, every other tool is refused.
"""

from clio_agent.sdk import Prefers, PromptFile, Subagent

explore = Subagent(
    "explore",
    prompt=PromptFile("prompt/subagents/explore.md"),
    description=(
        "Fast read-only search: finds what exists (files, data, task records, sources) and "
        "reports each finding with where it came from, so you get conclusions without the "
        "raw material. Say how thorough to be: quick, medium or thorough."
    ),
    derive="caller",
    effects="read",
    # The fleet's explore role (Fleet settings) picks a fast model; unset, it inherits.
    prefers=Prefers(role="explore"),
)

planner = Subagent(
    "planner",
    prompt=PromptFile("prompt/subagents/planner.md"),
    description=(
        "Read-only: designs a workflow for an assignment and returns it as run_workflow "
        "arguments in workflow_state, ready to start unchanged."
    ),
    derive="caller",
    effects="read",
    structured_outputs={"workflow_state": True},
)

review = Subagent(
    "review",
    prompt=PromptFile("prompt/subagents/review.md"),
    description=(
        "Read-only and independent: checks work or a claim against the material it rests "
        "on and returns a verdict with the evidence for each point."
    ),
    derive="caller",
    effects="read",
)
