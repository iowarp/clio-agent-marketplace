---
id: factorio.execution-boundary
section: domain
---
## Boundary for future Relay execution

This agent ends at a reviewable execution handoff. It may record the expected
command, required files, solver/license assumptions, outputs, and verification
signals so a future Relay adapter can submit it. Do not attempt to emulate that
adapter, invent job ids, or imply that a remote solver ran.
