---
id: hook-smoke.role
section: domain
---
Confirm whether this plugin's packaged hook is present and what it does: the
`hook-smoke.pre_message` prompt-submit hook denies any prompt containing the
`CLIO_HOOK_SMOKE_BLOCK` marker. Plugin hooks run only after the marketplace
trust step, so report the trust state you can observe rather than assuming it.
