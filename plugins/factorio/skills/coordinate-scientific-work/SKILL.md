---
name: coordinate-scientific-work
title: Coordinate Scientific Work
description: Use for scientific requests beyond greetings and conceptual questions, to decide whether to answer, clarify, load a method, do the work or brief one of Factorio's specialists.
keywords:
- level:L1
- factorio
- delegation
---

Clarification, a specialist consultation and independent parallel work are
for scientific requests that benefit from them; greetings and ordinary
questions need none of this.
[decision-criteria.md](references/decision-criteria.md) separates direct
answers, `ask_user`, focused skills, work run directly, one consultation and
independent fan-out, and says which specialist owns which question.

## Consultations

- One bounded consultation is `spawn_agent_task`. Several independent ones in
  one `spawn_agents_parallel` call are admitted or queued together. A queued
  task is accepted work, not a failure.
- A returned task id is the durable identity of that consultation, through
  observation, waiting, a child's question, a pause or context compaction; a
  replacement or duplicate for the same assignment is a second consultation of
  the same question. The task lifecycle itself (waiting, questions, pause,
  cancel) follows the runtime's task rules.
- Dependent work needs its prerequisites' results.

## Failures

A terminal failure, cancellation or unavailable tool is evidence about what
remains unresolved. A different specialist or memory does not fill that gap
silently; the limitation and its impact are part of the result, and
independent work can continue.

## Synthesis

Only settled results synthesize. Assumptions, units, provenance,
disagreements and confidence reconcile across results; which result changed
which decision is part of the science; incomplete or contradictory findings
stay explicit rather than resolved toward the most confident prose. The
coordination itself matters to the scientist only when it explains a blocker,
provenance or the next decision. A consultation completed when its returned
task state and result say so.
