---
id: genomics-review.guidance-2
section: domain
---
For any prompt that includes a FASTA path, reference sequence, reference
quality, contigs, GC content, ambiguous bases, or downstream reference
readiness, perform an executable sync delegation to `reference` before final
synthesis. Do not answer with prose saying the review requires delegation; call
the child expert and wait for its compact result.
When synthesizing returned FASTA evidence, preserve the exact contig identifiers
and per-contig values reported by the reference expert. If the returned evidence
names contigs such as `chrA` or `plasmidB`, those identifiers must appear
verbatim in the final answer.

For prompts that ask about variants, variant effects, genotype summary,
functional annotation, high-impact rows, or annotation risk outside cohort-QC
readiness, perform an executable sync delegation to `variants` before final
synthesis.

For collaborator handoff requests that include both a reference FASTA and a VCF,
delegate both `reference` and `variants` before final synthesis. After each
child returns, resume from the compact child evidence. If either child returns a
`NEXT_EXPERT` continuation contract for a declared quality or impact child,
execute that continuation before finalizing.

For prompts that combine cohort QC with reference or variant handoff, run
`cohort_qc` first, then delegate `reference` or `variants` as needed before
final synthesis. Final answers should preserve which evidence came from which
expert and should not blur a missing-manifest caveat into a clean pass.
