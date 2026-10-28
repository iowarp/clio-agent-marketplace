---
id: deep-research.options
section: domain
when: {"tools": ["run_flow"]}
---
Leave the `deep-research` options at their defaults unless the request calls
for more: `max_directions` (default 6) for a broad question, `max_rounds`
(default 2 gap-closing rounds) when the person wants depth or speed,
`concurrency` to run fewer researchers at once, and `researcher_model` or
`critic_model` when the person names models. `run_flow` returns a handle at
once; wait for the result with `wait_tasks`.
