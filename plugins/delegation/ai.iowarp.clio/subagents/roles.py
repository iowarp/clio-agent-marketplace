"""Generic roles every agent with delegation can start.

Each role runs the delegating agent's own plugins (``derive="caller"``), so a role
started by a manufacturing agent can read what that agent reads. All three are
read-only: tools that declare no side effects run, every other tool is refused.
"""

from clio_agent.sdk import PromptFile, Subagent

explore = Subagent(
    "explore",
    prompt=PromptFile("prompt/subagents/explore.md"),
    description=(
        "Read-only survey: finds what exists (files, data, task records, sources) and "
        "reports each finding with where it came from, so you get the findings without "
        "the raw material."
    ),
    derive="caller",
    effects="read",
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
