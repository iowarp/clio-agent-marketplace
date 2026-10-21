---
id: spotter.attention
section: domain
---
For captured model attention, start with `spotter_list_attention_calls` for the
parent session. `spotter_inspect_attention` takes an exact response id, recorded
decode-step indices and an optional versioned profile; carry its capture hash
and profile revision into findings. Its heat score is distinct from uniform mean
attention mass. Unretained positions are unknown: never fabricate transcript,
image-patch or A2UI coordinates from token positions, and when the mapping is
absent say so and request the recorded mapping. Attention strength alone is
neither poisoning evidence nor a reason to raise an alert or quarantine.
Separate observed evidence, hypotheses and uncertainty.

To present an attention finding, pass `raise_alert_card` an `attention_evidence`
object with the inspected `response_id`, `capture_sha256`, `steps`, resolved
`profile`, `profile_revision` and a concise `uncertainty`, copied from the
inspection result; CLIO binds them to the parent transcript, so never guess
message ids, token offsets or part revisions. If the tool reports unavailable
evidence, keep the finding and explain the limit; do not substitute another
capture or broaden the selected steps.
