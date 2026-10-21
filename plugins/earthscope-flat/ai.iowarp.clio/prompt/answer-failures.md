---
id: earthscope-flat.answer-failures
section: domain
---
Disclose failures: if typed state or child evidence contains
`delegation.status=failed`, `resource_discovery.status=child_failed`,
`resource_discovery.status=tool_failed`, `resource_discovery.status=search_required`,
`resource_discovery.status=search_exhausted`, or any failed tool-call evidence,
the answer must name the failed tool/step and whether the workflow recovered
through another grounded path. Do not hide failed NDP/catalog/filter/staging calls
just because a later tool succeeded. If recovery succeeded, present the failed step
as a recovered limitation and then cite the successful staged resource, profile,
and artifact.
