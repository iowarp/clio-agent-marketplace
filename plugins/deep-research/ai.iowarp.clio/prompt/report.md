---
id: deep-research.report
section: domain
when: {"tools": ["run_flow"]}
---
Read `get_task_result(handle=handle,
select=["/workflow_state/deep_research/delivery"])` for path, persistence, cited
`used` URLs, audit counts, gaps and review. Follow next_cursor; concatenate JSON
fragments before parsing. For verified persistence call
`create_artifact(kind="report", path=report_path, used=used)`; otherwise read
`/answer` and register unchanged Markdown. Summarize outcome, artifact, counts
and gaps. Review is judgment, not proof. Do not re-research or message a finished
flow for metadata. Explain failures without results.
