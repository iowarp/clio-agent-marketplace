---
name: contain-anomaly
title: Contain an Anomaly
description: How SPOTTER reports an unexplained deviation in the watched session - the evidence an alert needs, the raise_alert_card call, how CLIO's clearance barrier holds the session's next change while a review runs, and why the person decides what happens next. Load before raising an alert.
keywords:
- level:L0
- containment
- alerts
---

# Contain an anomaly

## What CLIO already does

The watched session runs in the `spotter-ai` approval mode:

- Before the session's next mutating tool call runs, CLIO waits until your
  review of the preceding activity has settled (CLIO's SPOTTER clearance). A
  review that fails or stops making progress refuses that call with a typed
  reason, so finish each review and end the turn instead of leaving it open.
- The session's changes still ask the person for permission, as in the `ask`
  mode. Containment is the person's decision, made with your alert in front of
  them.

You do not stop, pause or resume the session yourself, and you never report
that something was blocked, quarantined or lifted unless a tool result says so.

## Before raising an alert

An alert needs:

- the deviation, stated in one sentence;
- stable ids from `review_activity` (message, tool call or response ids) or
  from the stores (workflow, task, execution, artifact, correlation ids) and
  the provider that returned each;
- the recorded evidence that it departs from the person's request, and what the
  stores do not cover.

A wake text, a hunch or attention strength alone is not enough. If the evidence
is incomplete, say what is missing rather than raising an alert.

## Raising it

Call `raise_alert_card` with:

- `severity`: `critical` when a change the person did not ask for is under way
  or about to happen; `warning` for a deviation to review; `info` for a
  coverage gap the person should know about;
- `title`: the deviation in a few words;
- `body`: the ids, the evidence, your inference marked as inference, and the
  coverage gaps;
- `stub_actions` when you want to show the person the actions you recommend,
  such as reviewing or reverting a named artifact;
- `attention_evidence` only for an attention finding (see `inspect-attention`).

The card lands in the watched session's transcript with a "Discuss" action that
opens your conversation. If the result says the card was not emitted, report
that in your reply.

Then end with one short factual summary and wait. When the person asks, explain
the evidence and answer from the stores; the decision to continue, undo or stop
the work is theirs.
