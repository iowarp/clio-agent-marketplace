---
id: deep-research.rounds
section: domain
---
First identify the material subquestions, competing explanations, stakeholder
views, time-sensitive facts and primary-source families. Start every currently
independent direction at once with `spawn_agents_parallel`, giving each
`researcher` run a precise, non-overlapping question; spawn dependent follow-ups
with `spawn_agent_task` only after their evidence exists. Collect every accepted
child; queued or running work is accepted work, not failed work, so never
replace a child because capacity is temporarily unavailable. Read every
individual result: repeated runs of one subagent are independent evidence
packets, and a merged `workflow_state` is not the research ledger.

Treat the first fan-out as an initial round. Delegate a new researcher for each
branch the evidence opened (actors, venues, papers, standards, mechanisms,
disagreements, periods, counterexamples) whose answer could materially change
the synthesis, and keep adapting. Do not add work to inflate counts; the failure
to avoid is leaving a material branch unexplored after the research revealed
it. A packet that silently drops part of its assignment is still partial.
