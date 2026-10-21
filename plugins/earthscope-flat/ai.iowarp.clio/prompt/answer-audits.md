---
id: earthscope-flat.answer-audits
section: domain
---
Audit scan-limited evidence before writing. The profile tool reports separate
scopes: `rows_examined`/`rows_scanned` describe how many rows were read, while
`rows_profiled`/`numeric_summary_rows` describe the rows used for min/max/mean
statistics. If a time min/max appears in `numeric_summary`, it belongs only to
`numeric_summary_rows`, not to every row examined and not to the full file. Do
not write "1,000k rows", "30-s cadence", "nominal 30 s", "hours", "days",
"continuous", "no missing values", "no glitches", "low noise", "clean record",
"likely spans", or "typical NDP files" unless a tool explicitly reported
full-file row count, cadence, gap analysis, missing-value counts, or noise
criteria. Do not convert `rows_scanned`/`rows_profiled` into cadence, duration,
Hz, or completeness — a scan-limited profile is coverage evidence only. Preserve
uncertainty units (`0.033 m` ≈ 3.3 cm, not sub-cm). If such evidence is absent,
say only that the run produced a scan-limited profile and a first-N-row plot, and
that full-file cadence/duration/gap quality was not verified. If missing-value
counts are present, report their scope exactly as `missing_values_scope=profiled_rows`
and `missing_values_rows`; do not call that full-file completeness. Do not
interpret `qChannel` numeric values as decoded quality. Avoid "good data", "high
quality", "quality flag high", "high-quality GNSS time-series", "suitable for
deformation analysis", or "low noise" unless the tool evidence includes explicit
QC decoding or suitability criteria.

**Scan-limited synthesis rules.** Small-model runs have
violated these three; hold them tight — grounding, not handcuffs:

- No cadence / duration / continuity generalization beyond the visible sample
  spacing. You may state the spacing between the rows a tool actually returned;
  you may NOT extrapolate it into a full-file sampling rate, record length,
  "continuous"/"gap-free" coverage, or a projected span. Visible sample spacing
  is a local observation, not a property of the file.
- No date-span or freshness claims ("spans 2019–2024", "recent", "up to date",
  "last updated", "N years of data") unless a child's typed workflow_state
  carries that field verbatim. If no typed state field asserts a date range or
  recency, say the run did not establish coverage dates — do not infer them from
  a filename, a station code, or a first/last visible timestamp.
- Profile numbers only from tool output. Every row count, min/max, mean,
  uncertainty, and column name in the answer must be COPIED from the profile
  tool's returned evidence. Do not compute, round beyond the reported precision,
  or reconstruct a statistic the tool did not return.
