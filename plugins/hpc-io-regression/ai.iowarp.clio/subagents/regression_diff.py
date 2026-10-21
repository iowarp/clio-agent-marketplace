"""Regression Diff Expert: a defined subagent of hpc-io-regression."""

from clio_agent.sdk import PromptFile, Subagent

regression_diff = Subagent(
    "regression_diff",
    prompt=PromptFile("prompt/subagents/regression_diff.md"),
    description="Regression Diff Expert: hpc regression diff",
    plugins=[],
    tools=["load_skill"],
)
