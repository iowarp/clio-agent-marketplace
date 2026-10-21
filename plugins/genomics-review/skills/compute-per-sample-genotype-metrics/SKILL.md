# Compute Per-Sample Genotype Metrics

For each sample in a multi-sample VCF, preserve:

- sample id,
- variants seen,
- called and missing genotype counts,
- call rate,
- heterozygosity,
- het/hom ratio when available,
- genotype-count breakdown.

Treat this as evidence extraction, not final judgment. Return enough compact
rows for the outlier expert to explain why a sample was flagged.
