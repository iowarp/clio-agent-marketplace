---
id: deep-research.options
section: domain
when: {"tools": ["run_flow"]}
---
The flow's planner sizes the run to the question. Set `max_directions` only when
the person asks for a limit, `max_rounds` (default 2 gap-closing rounds) when they
want depth or speed, `concurrency` to run fewer researchers at once, and
`researcher_model` or `critic_model` when they name models or a large exploration
is better split across cheaper researchers. `run_flow` returns a handle at
once; wait for the result with `wait_tasks`.
