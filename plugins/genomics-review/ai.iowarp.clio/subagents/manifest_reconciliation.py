"""Manifest Reconciliation Expert: a defined subagent of genomics-review."""

from clio_agent.sdk import PromptFile, Subagent

manifest_reconciliation = Subagent(
    "manifest_reconciliation",
    prompt=PromptFile("prompt/subagents/manifest_reconciliation.md"),
    description="Manifest Reconciliation Expert: genomics manifest reconciliation",
    plugins=[],
    tools=["load_skill"],
)
