---
name: audit-dataset
title: Audit a Dataset in a Child Agent
description: Inspect one dataset in a child, adapt checks to its real files and the parent's question, and return grounded findings, source references, optional outputs and unresolved scientific questions.
effect: spawn_subagent_with_skill
keywords:
- level:L0
- data-onboarding
- delegation
---

This skill runs inside the delegated child, which does the assigned inspection
itself.

The assignment names the source bundle and usually the question or audit scope.
An unreadable source is an access problem, and that problem is itself a finding.
Notes, code and outputs live in the workspace so the source stays as delivered;
the default place is the Agent workspace state at
`<workspace_state>/datasets/<key>/` (resolved from
`CLIO_AGENT_WORKSPACE_STATE_DIR`), unless the parent's assignment names another.

`onboard-dataset` covers inspecting the files. Domain or source skills the parent
names cover scientific and format checks, and a source skill that states a
version contract defines which versions it supports. Scripts, cards and schemas
are optional aids whose assumptions may not fit a given dataset.

Treatment meanings, units, calibration and identity mappings that remain
uncertain are questions for the parent; a guess or a source edit hides them.
Checks that do not depend on their answers are unaffected by them.

Calculations and outputs are trustworthy to the extent they match source
observations, counts and join behavior. Process completion or a passing example
schema alone does not establish scientific validity. Converting a whole dataset
just to fill a required set of tables adds no evidence. The parent owns final
presentation.

What the parent can use from the child: the inspected scope, evidence, findings,
limitations, questions, paths of any notes/code/outputs, and checks with their
results; for reusable code, its invocation and dependencies; whether a loader or
views were needed; and any specific unfinished work.

The parent checks the evidence supporting its answer: inspecting a sample,
repeating a calculation, comparing counts or rerunning selected code when
warranted. A second execution of the entire pipeline is not required. A partial
result is useful when it is labelled as partial. The assigned scope is done when
it is satisfied or a concrete access or interpretation dependency remains.