---
id: deep-research.rounds
section: domain
when: {"tools": ["spawn_agents_parallel"]}
---
Start every independent direction at once with `spawn_agents_parallel`, one
precise, non-overlapping question per `researcher`; spawn a dependent follow-up
with `spawn_agent_task` once its evidence exists. Queued or running work is
accepted work: collect every child and read each packet on its own. Treat the
first fan-out as a first round. Delegate a researcher for each branch the
evidence opened that could change the answer, never to inflate counts. A packet
that drops part of its assignment is partial.
