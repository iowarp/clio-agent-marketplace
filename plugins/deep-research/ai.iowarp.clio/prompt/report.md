---
id: deep-research.report
section: domain
when: {"tools": ["run_flow"]}
---
`get_task_result(handle=handle,
select=["/workflow_state/deep_research/delivery"])` returns path, persistence, cited
`used` URLs, audit counts, gaps and review, paged by next_cursor; its JSON fragments
parse once concatenated. With verified persistence,
`create_artifact(kind="report", path=report_path, used=used)` registers it;
otherwise `/answer` holds Markdown to register unchanged. The person needs outcome,
artifact, counts and gaps. Review is judgment, not proof. A finished flow already
holds its metadata; re-research or messages add nothing. A failure without results
needs explaining.
