"""Cohort Outlier Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

cohort_outliers = Subagent(
    "cohort_outliers",
    prompt=PromptFile("prompt/subagents/cohort_outliers.md"),
    description="Cohort Outlier Expert: genomics cohort outliers",
    plugins=[],
    tools=["load_skill"],
)
