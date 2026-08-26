# phenotype-workload

The synthetic phenotyping workload behind the `phenotype` pack: a
deterministic 5-stage pipeline (ingest -> calibrate -> segment ->
extract_traits -> predict) over a fixed 60-plant cohort, with full provenance
capture per stage execution into a SQLite store, quarantine semantics, batch
reports, and the chaos-engineering `injection.json` hook for validating
anomaly detection.

Split out of `spotter-ai/impl` on owner ruling: the SPOTTER provenance MCP
(general, reads Flowcept/CMF/native stores) and this synthetic demo science
are **two different things** and ship as two projects. The SPOTTER server
reads the provenance store this workload writes — that contract is exercised
at the pack boundary, not by shared code.

Entry points:

- `phenotype-mcp` — the 3-tool workload MCP (`measure_cohort`,
  `campaign_status`, `lift_quarantine`), declared by `phenotype/AGENT.md`.
- `spotter-campaign` — the batch campaign CLI.

Test with `uv run --project . pytest`.
