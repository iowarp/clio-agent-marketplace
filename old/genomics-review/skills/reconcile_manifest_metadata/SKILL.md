# Reconcile Manifest Metadata

Compare available manifest evidence against metric-derived QC findings. Check
sample IDs, expected sex or chromosome evidence if supplied, relatedness notes,
duplicate identifiers, and any explicit user-provided sample labels.

Do not infer a sample swap or sex mismatch without manifest evidence. If the
manifest is absent, return the missing-manifest caveat and explain which claims
remain unverified.
