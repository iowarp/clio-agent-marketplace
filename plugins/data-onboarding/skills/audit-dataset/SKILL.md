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

You are already running this skill in the delegated child. Complete the assigned
inspection directly; do not recursively delegate it.

The assignment must identify the source bundle and should identify the question
or audit scope. If the source is unreadable, report the actual access problem.
Write notes, code and outputs to the workspace so the source stays as
delivered, by default in the Agent workspace state at
`<workspace_state>/datasets/<key>/` (resolved from
`CLIO_AGENT_WORKSPACE_STATE_DIR`), or wherever the parent's assignment says.

1. Load `onboard-dataset` and inspect the files needed for the assignment. Load
   the domain or source skills the parent names for scientific and format
   checks, and follow a source skill's version contract when it states one.
   Scripts, cards and schemas are optional aids. Adapt or replace them when
   their assumptions do not fit.
2. Keep uncertain treatment meanings, units, calibration and identity mappings
   explicit. Return these questions to the parent rather than guessing or
   editing the source. Continue checks that do not depend on their answers.
3. Check calculations and outputs against source observations, counts and join
   behavior. Process completion or a passing example schema alone does not
   establish scientific validity. Do not convert a whole dataset merely to fill
   a required set of tables. The parent owns final presentation.
4. Return a concise account of inspected scope, evidence, findings, limitations,
   questions, paths of any notes/code/outputs, and checks with their results.
   For reusable code, include its invocation and dependencies. If no loader or
   views were needed, say so. Identify any specific unfinished work.

The parent checks the evidence supporting its answer: inspecting a sample,
repeating a calculation, comparing counts or rerunning selected code when
warranted. A mandatory second execution of the entire pipeline is not required.
A partial result must be labelled accurately. Continue until the assigned scope
is satisfied or a concrete access or interpretation dependency remains.
