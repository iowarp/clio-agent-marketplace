---
name: inspect-attention
title: Inspect Attention
description: Find what steered the watched session's answer - attention_sources(message_id) on an answer (or an exact quoted passage of it) returns labelled sources, the transcript blocks it weighted with their hottest excerpts, and evidence to carry into raise_alert_card; spotter_list_attention_calls and spotter_inspect_attention read the raw capture for a deep dive. Load when a question is whether an input steered a model call.
keywords:
- level:L0
- attention
- provenance
---

# Inspect attention

Attention capture is optional: it needs a model served with capture, Flowcept
among the provenance providers and a local capture directory
(`provenance.attention.files_dir`). When it is unavailable, the tools say so
with a typed reason. Say so and continue with the other evidence.

## Ask about a passage

When an answer or an action looks off, call `attention_sources`:

- the simplest call passes only `message_id` from
  `review_activity.assistant_answers` and omits `text`: it explains that whole
  answer (bounded); omit both to explain the latest answer;
- to check one claim, add `text`: the passage quoted exactly as it appears in
  the assistant's answer or in the reasoning behind a tool call (one
  contiguous sentence or claim). Never quote the user's message or a tool
  result: they have no attention, and the call returns
  `selection_not_located`.

`selection.basis` says what was explained (`answer`, `reasoning`, a `_tail`
when bounded, or `quoted`).

It returns:

- `sources`: the share of attention per source domain (`user`, `tool_result`,
  `system`, `tool_call`, `thinking`, ...), largest first;
- `sections`: the top labelled prompt sections (for example one tool's result);
- `blocks`: the transcript blocks it weighted most (a tool result, an earlier
  answer, a tool input), each with its hottest `excerpts`;
- `flags`, such as `tool_result_dominant`;
- `evidence`: the exact capture receipt for an alert.

An error carries a `hint` with the next step: re-quote the passage exactly
from the answer, quote a longer unique passage, or omit `text` and pass only
`message_id`.

## Reading the result

- Read the hottest excerpts: are they the person's request and the evidence
  the answer should rest on, or something else?
- Pasted data or a replayed tool output inside a user message is labelled
  `user` because it sits in the user's turn; look at the excerpt itself to
  tell the person's words from the data they supplied.
- Attention strength alone is neither evidence of poisoning nor a reason to
  raise an alert. It supports a finding only next to recorded evidence that the
  steered action or answer departed from the request.
- Sparse capture: an absent position is unretained, not zero attention. Shares
  are the uniform mean attention mass over the selected steps.
- Separate observed evidence, hypotheses and uncertainty.

## Raw capture (deep dive)

`spotter_list_attention_calls` for the watched session's id lists recorded
model response ids with `capture_available` and `decode_steps` (how many decode
steps the capture holds); it does not verify the capture file itself.
`spotter_capabilities` says whether this reader is configured; when it is not,
these tools return `attention_not_configured`.

`spotter_inspect_attention` takes:

- an exact `response_id` from the listing;
- optional `steps`: omit them to inspect the whole response. To narrow it, pass
  decode-step indices within `0..decode_steps-1`; never estimate steps from
  character offsets;
- an optional versioned `profile` (the uniform mean is the default).

An `invalid_argument` error names the valid range; fix the call and retry. Other
codes (`attention_capture_partial`, `attention_file_mismatch`,
`attention_record_malformed`) mean the evidence itself is unusable: say so.

It verifies the local capture file and returns the capture hash, the resolved
profile and its revision, per-source scores, top tokens, coverage and
limitations. The profile's heat score is distinct from the uniform mean
attention mass: report which one you are quoting. Coordinates are captured
prompt tokens; never turn them into transcript, image-patch or A2UI
coordinates.

## Presenting a finding

To show an attention finding, pass `raise_alert_card` an `attention_evidence`
object: copy `response_id`, `capture_sha256`, `steps`, `profile` and
`profile_revision` from the `evidence` of `attention_sources` (or from a raw
inspection) and add a concise `uncertainty`. CLIO binds these to the watched
session's transcript and verifies the receipt against its local capture, so
never supply message ids, token offsets or part revisions yourself. If the tool
reports the evidence unavailable, keep the finding and explain the limit; do not
substitute another capture or widen the selected steps.
