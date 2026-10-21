---
id: phenotype.campaign
section: domain
---
The phenotype tools run a real pipeline (ingest, calibrate, segment, extract
traits, predict), and every stage execution is recorded to a provenance store.
Run a campaign in batches: call `phenotype_measure_cohort` with about 5 runs per
call, report that batch's headline metrics in one short line, and continue
until the requested total (run numbering continues across calls). Finish with a
short quantitative summary of the whole campaign. Keep responses short and
quantitative.
