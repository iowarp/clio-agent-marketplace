# Coordinate Cohort QC Map/Reduce

Use a three-step cohort QC pattern:

1. Extract per-sample genotype metrics from the VCF.
2. Merge those metrics into cohort-level outlier interpretation.
3. Reconcile the outlier set against manifest evidence when available.

For executable CLIO hierarchy runs, keep the phases as separate child expert
delegations. Do not repeat the metric child when the metric evidence already
returned successfully; continue to outlier interpretation, then manifest
reconciliation. When no manifest was provided, the reconciliation phase still
returns an explicit missing-manifest caveat instead of silently skipping the
child.

Keep these roles separate in the final answer. Metric extraction proves call
rate, missingness, heterozygosity, and het/hom ratio. Cohort outlier merging
turns those metrics into preliminary keep/drop advice. Manifest reconciliation
can confirm identity/sex/sample-swap issues only when manifest evidence exists.
