---
name: inspect-attention
title: Inspect Attention
description: Find what steered the watched session's answer - attention_sources(message_id) on an answer (or on an exact quoted passage of it) returns the labelled sources and the transcript blocks the answer weighted most, each with its hottest excerpts. Load when the question is whether an input steered a model call.
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
- `evidence`: the exact capture receipt it was computed from.

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

## Presenting a finding

When attention informed a finding, describe it in the alert's body: which
sources and excerpts the answer weighted most, and what that does and does not
show. The person can explore attention themselves by selecting the passage in
the answer.
