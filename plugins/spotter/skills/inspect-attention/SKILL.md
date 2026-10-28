---
name: inspect-attention
title: Inspect Attention
description: Read captured model attention for the watched session with spotter_list_attention_calls and spotter_inspect_attention - exact response ids, recorded decode steps, versioned profiles, coverage and uncertainty - and carry the evidence into a finding or an alert card without guessing coordinates. Load when a question is whether an input steered a model call.
keywords:
- level:L0
- attention
- provenance
---

# Inspect attention

Attention capture is optional. It needs Flowcept among the provenance providers
and a local capture directory (`provenance.attention.files_dir`).
`spotter_capabilities` says whether it is configured; when it is not, the tools
return `attention_not_configured`. Say so and continue with the other evidence.

## Find the call

Start with `spotter_list_attention_calls` for the watched session's id. It lists
recorded model response ids; listing does not verify that a capture exists or is
intact.

## Inspect it

`spotter_inspect_attention` takes:

- an exact `response_id` from the listing;
- `steps`: recorded decode-step indices. Use recorded mappings; never estimate
  steps from character offsets;
- an optional versioned `profile` (the uniform mean is the default).

It verifies the local capture file and returns the capture hash, the resolved
profile and its revision, per-source scores, top tokens, coverage and
limitations. Carry `capture_sha256` and `profile_revision` into every finding.

## Reading the result

- The profile's heat score is distinct from the uniform mean attention mass.
  Report which one you are quoting.
- Sparse capture: an absent position is unretained, not zero attention.
- Coordinates are captured prompt tokens. Never turn token positions into
  transcript, image-patch or A2UI coordinates; when the mapping you need is
  absent, say so and ask for the recorded mapping.
- Attention strength alone is neither evidence of poisoning nor a reason to
  raise an alert. It supports a finding only next to provenance evidence that
  the steered action departed from the request.
- Separate observed evidence, hypotheses and uncertainty.

## Presenting a finding

To show an attention finding, pass `raise_alert_card` an `attention_evidence`
object copied from the inspection result: `response_id`, `capture_sha256`,
`steps`, the resolved `profile`, `profile_revision` and a concise `uncertainty`.
CLIO binds these to the watched session's transcript and verifies the receipt
against its local capture, so never supply message ids, token offsets or part
revisions yourself. If the tool reports the evidence unavailable, keep the
finding and explain the limit; do not substitute another capture or widen the
selected steps.
