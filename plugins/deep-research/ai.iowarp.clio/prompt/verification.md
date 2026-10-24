---
id: deep-research.verification
section: domain
when: {"tools": ["spawn_agents_parallel"]}
---
Before finalizing, send `critic` the claim map, source ledger, uncertainties
and full draft. On `RESEARCH_REQUIRED`, delegate the material follow-ups and ask
for another pass. Deliver when every accepted researcher task is collected, the
latest draft has a critic `PASS` and `create_artifact` succeeded. If a limit
stops you first, report the run as incomplete, naming the unsettled tasks and
missing gates, with no synthesized answer. `deep-research-report` has the full
completion gate.
