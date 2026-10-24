---
id: deep-research.report
section: domain
when: {"tools": ["run_flow"]}
---
The run's result carries the report as `answer`; its
`workflow_state.deep_research` holds `report_path`, `verified`, `rejected` and
`gaps_unresolved`. Deliver the report with `create_artifact`: `path` set to
`report_path` (without one, the `answer` unchanged as `content` under a `.md`
name), `kind="report"`, `used` set to each verified `source_url`. Then
summarize the conclusion, the artifact, the verified and rejected counts and
the unresolved questions. Never re-research what the run returned or add facts
to it. If the run ended without a result, say how and give no answer yourself.
