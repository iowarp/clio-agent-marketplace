---
id: phenotype.quarantine
section: domain
---
If a tool reports the campaign HALTED or quarantined, relay that status
verbatim and stop. Do not retry and do not lift the quarantine on your own.
Only when the user explicitly says SPOTTER has cleared it: check
`phenotype_campaign_status`, call `phenotype_lift_quarantine` only if still
quarantined, then resume the remaining runs. Never speculate about why a run
was quarantined; that investigation belongs to SPOTTER.
