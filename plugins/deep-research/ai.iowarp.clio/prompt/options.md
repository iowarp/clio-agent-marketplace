---
id: deep-research.options
section: domain
when: {"tools": ["run_flow"]}
---
The flow's planner sizes the run to the question. `max_directions` caps directions
when the person asks for a limit, `max_rounds` (default 1 follow-up round, which a
coordinator uses only when the evidence needs it) trades depth for speed, `concurrency` runs fewer researchers at once, and
`researcher_model` or `critic_model` pick models, which also lets a large exploration
split across cheaper researchers. `run_flow` returns a handle at
once; `wait_tasks` returns the result.
