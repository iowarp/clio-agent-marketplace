---
id: earthscope-gnss-region-width.guidance-3
section: domain
---
If typed state or compact child evidence contains `delegation.status=failed`,
`resource_discovery.status=child_failed`, `resource_discovery.status=tool_failed`,
`resource_discovery.status=search_required`, `resource_discovery.status=search_exhausted`,
or any failed tool-call evidence, the user-facing answer must disclose the
failed tool/step and whether the workflow recovered through another grounded
path. Do not hide failed NDP/catalog/filter/staging calls just because a later
tool succeeded. If recovery succeeded, present the failed step as a recovered
limitation and then cite the successful staged resource, profile, and artifact.

Before writing the final user-facing answer, audit scan-limited evidence. The
profile tool reports separate scopes: `rows_examined`/`rows_scanned` describe
how many rows were read, while `rows_profiled`/`numeric_summary_rows` describe
the rows used for min/max/mean statistics. If a time min/max appears in
`numeric_summary`, it belongs only to `numeric_summary_rows`, not to every row
examined and not to the full file. Do not write "1,000k rows", "30-s cadence",
"nominal 30 s", "hours", "days", "continuous", "no missing values", "no
glitches", "low noise", "clean record", "likely spans", or "typical NDP files"
unless a tool explicitly reported full-file row count, cadence, gap analysis,
missing-value counts, or noise criteria. If such evidence is absent, say only
that the run produced a scan-limited profile and a first-N-row plot, and that
full-file cadence/duration/gap quality was not verified.
If missing-value counts are present, report their scope exactly as
`missing_values_scope=profiled_rows` and `missing_values_rows`; do not call that
full-file completeness. Do not interpret `qChannel` numeric values as decoded
quality. Avoid "good data", "high quality", "quality flag high", "high-quality
GNSS time-series", "suitable for deformation analysis", or "low noise" unless
the tool evidence includes explicit QC decoding or suitability criteria.
