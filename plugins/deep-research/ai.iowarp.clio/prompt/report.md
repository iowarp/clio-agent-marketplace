---
id: deep-research.report
section: domain
when: {"tools": ["run_flow"]}
---
Use `workflow_state.deep_research`. Saved delivery requires
`persistence.status="verified"`. Call `create_artifact` with `kind="report"`,
`path=report_path`, and `used` listing all `verified[].evidence[].source_url`s.
Without a path, use unchanged `answer` as `.md` content. Summarize the outcome,
artifact, cumulative verified/rejected counts and `gaps_unresolved`.
`report_reviews` records model judgment, not proof. Do not re-research or add
facts. If the run failed without a result, explain the failure.
