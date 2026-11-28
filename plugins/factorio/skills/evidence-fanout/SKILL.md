---
name: evidence-fanout
title: Coordinate Scientific Evidence Fan-out
description: Use (as evidence_researcher) to split one evidence question into independent source lanes, follow leads, obtain criticism and return a complete source audit.
keywords:
- level:L1
- factorio
- evidence
---

This is how `evidence_researcher` runs a dynamic evidence investigation; it
has no fixed lane count and is not a generic literature review.

[fanout-lifecycle.md](references/fanout-lifecycle.md) covers lane
boundaries, parallel spawn/wait behavior, evidence-driven follow-ups, critic
iteration, and blocked-task handling.
[source-integrity.md](references/source-integrity.md) covers fetched-source
rules, claim mapping, citation placement, source disposition, and
incomplete-evidence reporting.

The coordinator has no web search. Web discovery and reading belong to
`evidence_leaf`, independent verification to `evidence_critic`. A
scientist-owned definition or inclusion choice that sets the evidence boundary
is the scientist's (`ask_user`). Each child's task id identifies its lane,
and the synthesis contains only returned evidence.
