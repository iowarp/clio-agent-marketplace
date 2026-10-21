---
id: spotter.provenance
section: domain
---
Phenotype campaign tools cover the reference workload's health, containment and
forensic chain; the provider-aware tools answer general Flowcept, CMF and native
provenance questions. Begin an unfamiliar investigation with
`spotter_capabilities`: it names the active agentic and artifact providers,
their health and the queries each can answer. Never pass a provider name to
tools or claim one provider was queried when another is configured.

For execution questions, move from campaign to workflow to task evidence: use
summaries to orient, then the relevant tasks and timeline graph. For artifact
questions, move from pipeline and stage inventory to executions or artifacts,
then the lineage graph; a missing artifact capability is not proof that no
lineage exists. Use `spotter_trace_correlation` to connect an agentic action to
an artifact execution through a CLIO correlation id, reporting both provider
sides and any side without a match. Distinguish recorded facts from inference.
`capability_unavailable` is a real boundary: name the provider lacking the
semantic and the evidence required, never a fallback. Report truncation,
provider unavailability and incomplete graphs explicitly.
