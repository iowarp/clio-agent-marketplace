---
id: genomics-review.guidance-3
section: domain
---
After `cohort_qc` returns a completed drop/keep advisory plus any manifest
caveat for a QC-only prompt, synthesize the final answer. Do not delegate back
to `cohort_qc` or broaden into `variants` unless the returned evidence says a
required child failed or the original request explicitly asks for variant
interpretation.
