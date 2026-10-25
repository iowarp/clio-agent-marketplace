---
id: deep-research.report
section: domain
when: {"tools": ["run_flow"]}
---
Use `workflow_state.deep_research`. Claim saved delivery only if
`persistence.status` is `verified`. Call `create_artifact` with `kind="report"`,
`path=report_path` (without one, unchanged `answer` as `content` under a `.md`
name), and `used` listing verified `source_url`s. Summarize the conclusion,
artifact, cumulative verified/rejected counts and `gaps_unresolved`. Do not
re-research or add facts. If the run failed without a result, explain the failure.
