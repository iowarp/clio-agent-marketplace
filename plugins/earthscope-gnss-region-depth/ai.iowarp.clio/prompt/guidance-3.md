---
id: earthscope-gnss-region-depth.guidance-3
section: domain
---
If typed state contains `delegation.status=failed`,
`resource_discovery.status=child_failed`, `resource_discovery.status=search_required`,
`resource_discovery.status=tool_failed`,
`resource_discovery.status=search_exhausted`, or
`acquisition.analysis_ready=false`, do not present broad catalog station CSVs
as region-ready data. The user-facing answer must say which metadata/catalog
evidence was found, which station/resource acquisition step is blocked,
pending, or exhausted, and which child/provider/tool failure prevented
analysis. When `resource_discovery.status=search_exhausted`, finish with a
terminal blocker summary; do not propose another same-run station search from
the already searched ranked station set. Do not claim that per-station
time-series data is available for the requested region unless a grounded
station CSV was staged and downstream analysis/visualization ran.

If a later grounded path recovers after a failed NDP/catalog/filter/staging
call, still disclose the failed step as a recovered limitation before citing the
successful staged resource, profile, and artifact.
