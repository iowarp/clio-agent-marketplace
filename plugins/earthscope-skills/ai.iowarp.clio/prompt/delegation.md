---
id: earthscope-skills.delegation
section: domain
---
Select and load the task-level procedure before starting any child. A request
comparing station coverage across regions loads `compare-earthscope-coverage`
before any regional resolution, delegation or catalog work. A skill with
`effect: spawn_subagent_with_skill` is an action, not documentation: running it
with a task creates a child, so never invoke it speculatively. Delegate only
when the loaded procedure directs it and every prerequisite it names is
available; for a coverage comparison the parent already holds the literal
cleaned catalog path and verified columns before creating any child.
