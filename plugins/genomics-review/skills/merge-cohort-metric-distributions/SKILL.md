# Merge Cohort Metric Distributions

Interpret sample metrics relative to the cohort distribution. Flag samples
below the configured call-rate threshold, samples with high heterozygosity
z-scores, and samples whose metrics are too sparse for confident conclusions.

The merge output should separate:

- strong drop candidates,
- samples needing manual review,
- clean samples,
- limitations caused by low variant count, malformed rows, or truncated sample
  output.
