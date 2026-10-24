---
name: coordinate-scientific-work
title: Coordinate Scientific Work
description: Decide whether to answer, clarify, load a method, run the work yourself or consult Factorio's specialists, pick the right specialist, brief it, and synthesize only settled results. Greetings and ordinary conceptual questions are answered directly and do not need this skill.
keywords:
- level:L1
- factorio
- delegation
---

Use this skill when a scientific request may benefit from clarification, a
specialist consultation, or independent parallel work. It is not a prelude to
greetings or ordinary questions.

Before delegating, read [decision-criteria.md](references/decision-criteria.md):
it separates direct answers, `ask_user`, focused skills, work you run
yourself, one consultation and independent fan-out, and says which specialist
owns which question.

## Starting consultations

- One bounded consultation: `spawn_agent_task`. Several independent ones:
  one `spawn_agents_parallel` call, so the runtime admits or queues them
  together. A queued task is accepted work, not a failure.
- Record every returned task id with its agent and assignment. The task id is
  the durable identity of that consultation: keep it through observation,
  waiting, a child's question, a pause or context compaction, and never start
  a replacement or duplicate for the same assignment. The task lifecycle
  itself (waiting, questions, pause, cancel) follows the runtime's task rules.
- Spawn dependent work only after its prerequisites have returned.

## Failures

Treat a terminal failure, cancellation or unavailable tool as evidence about
what remains unresolved. Do not silently retry with a different specialist or
fill the gap from memory. Continue independent work where useful, then report
the exact limitation and its impact.

## Synthesis

Synthesize only settled results. Reconcile assumptions, units, provenance,
disagreements and confidence; say which result changed which decision; keep
incomplete or contradictory findings explicit rather than choosing the most
confident prose. Report the science first, and mention the coordination only
when it explains a blocker, provenance or the next decision. Never say a
consultation completed until its returned task state and result say so.
