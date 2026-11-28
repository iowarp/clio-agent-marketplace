---
name: run-a-study
title: Run a study
description: Use to run a study in the study log, from a small experiment run in this conversation to competing hypotheses tested by parallel workflow branches - cited observations, measurements as data, a view of the results, and a conclusion that cites its entries.
keywords:
- method
- study
- hypotheses
- workflow
---

# Run a study

The log records what was learned; the workflow runs the work. The log never judges a
claim: the analysis, what is enough, and why are the agent's, stated in the entries.
The log is the study's record: the person reads the study in its Science log, follows
each claim to the entries and calls behind it, and can export the measurements. A
result that is only in a chat answer cannot be checked.

## The question and its hypotheses

- **Question** (`log_entry`, `type: question`): the statement and its scope. A limit
  the person gave on what the study may spend lives on this root question as `budget`
  (amount and unit), and every Observation then carries its `cost`.
- **Hypothesis**, one per competing answer (`links: {question: <id>}`), each with the
  `refuting_prediction` that would show it wrong. A hypothesis that states a law can
  carry it as `formula`, written `<measured> = <expression>` in the names the data use
  (the apparatus's inputs, a table's columns), with numbers, `+ - * / ^`, parentheses,
  `pi` and `sqrt exp log abs min max`; a threshold is a `max` or `min`. A formula in
  the data's own names can be drawn against every reading.
- **Size.** The claims set it. A claim that one approach beats another needs each
  approach tried under shared conditions (the same inputs, seeds or settings), often
  enough that the difference stands out from the run-to-run spread; a single trial
  supports neither. A short pilot or the first trials estimate that spread: a sample
  whose interval stays wider than the difference worth reporting cannot decide between
  the hypotheses, and when nothing limits the study a larger sample can. A claim about
  a law needs measurements across the range it covers. The intended sample size belongs
  on each Experiment; a sample too large for one conversation is work for children.

## Small or branched

A small study, one experiment that fits in this conversation, needs no workflow: its
entries (question, hypotheses, experiment, observations, evidence, conclusion and a
chart) are written in the conversation, with no branches to read or merge. Values
recorded as `measurements` can be charted: for a small study one dashboard holding the
chart that answers the question is the whole view (a few calls with
`create-dashboard`). The record costs a few calls; it gives the person a result they
can check, see and reuse. A branched study suits separable parts: competing hypotheses
that each need their own test, independent inputs, many trials.

## Branches

- **The workflow.** `run_workflow` with `isolate: true` gives each step its own folder:
  one step per hypothesis with target `self`, a merge step after them, and `review`
  named in `editors`. An editor acts when a step fails, or when it runs as a step: a
  step targeting `review` after the merge reads its result and, when the evidence
  cannot decide, adds the steps that would (a larger sample, a new condition) and a
  merge after them. Each step's task names its hypothesis id and covers designing,
  running and analyzing the test. The branch is where a result no hypothesis offered is
  first seen and pursued; a branch told only to gather data and report it back has no
  results of its own to change course from.
- **Experiment** (`links: {hypothesis: <id>}`): the method and the intended sample
  size, written before observations. A design formed before reading what other branches
  found is independent of them. Independent trials are separable work: children each
  take a self-contained batch with its conditions and the Observations to log, so each
  child's context holds only its own trials, the parent's holds their results, and the
  batches run side by side.

## Observations and evidence

- **Observation**, one per run (`links: {experiment: <id>}`). `from_calls` cites the
  recorded calls that produced it: every tool result carries its `call:` reference.
  Values go in `measurements` with their `conditions` (settings, seed, strategy, node,
  repeat index). A value a tool returned is named with `source: {call, field}`, not
  typed. A result file written by the agent's own script, designated as an artifact,
  has its hash on record.
- **Other branches.** `query_log` reads them; Evidence that relies on another branch's
  result says so.
- **Evidence** (`links: {observation: [...], supports | refutes: <hypothesis>}`).
  `export_measurements` writes the measurements to a data file with a manifest; the
  analysis the experiment needs (a mean, a paired comparison over shared conditions,
  an interval, a fitted model) runs in the agent's own code, with its seed recorded
  when it is random, and that call is the Evidence's `analysis_call`. `strength` is
  honest, including when the sample is too small to separate two hypotheses.
  `set_status` records a hypothesis's fate (supported, refuted, superseded) and the
  reason. A branch's own results are analyzed in the branch, even when the merge will
  compare all of them.

## Changes of course

- **A new explanation.** A pattern, an outlier or a cause no hypothesis offered is a
  new hypothesis; `fork` with a note naming it carries the conversation and pursues the
  new direction beside the branch, and the merge waits on it.
- **A new question.** When the question itself should change (its premise is false, or
  each answer holds only under conditions the question did not name), a new Question
  and a Reframe (`links: {old_question, new_question, evidence}`) record it. In a
  workflow a fork with a note naming the new question pursues it. The Conclusion
  answers the question the study ended with.

## The conclusion

The merge step reads every branch's entries and writes one Conclusion
(`links: {question: <root id>, merges: [...]}`): each claim cites the entries it rests
on, a quantitative claim cites its analysis call, `confidence` and `caveats` are
explicit, and `relation` says whether it answers the question, refutes its premise or
replaces it. A Conflict records each unresolved disagreement, citing both sides:
between branches, or between two results (a measurement and a calculation, two
methods) that should agree. A comparison shows as a chart from the measurements, not
as prose alone.

## Views

A study's views are where the scientist watches it run and checks its conclusion.
They are dashboards, built around the question: what would show whether a
hypothesis holds, how the branches compare, where the study is now. A view is a
dashboard built with the `create-dashboard` skill (`review-visual-presentation`
reviews it), published with `publish_dashboard_report`, and attached with `log_entry`
(`type: view`, `dashboard_id`: the report id it returned, a `title`, the `purpose` it
serves, `links: {serves: <question or hypothesis>}`). A chat surface is for a quick
look in the conversation, not a study view.

A chart or table in a view can read the study directly, and it shows new entries as
they arrive without being rebuilt:

- `study://<study>/measurements`: every measured value with its conditions, branch
  and status; when a standing hypothesis gives a `formula` in the data's own names,
  each row also carries the law's prediction (`law_value`) and the law (`law`).
- `study://<study>/entries`: every entry with its type, branch, status and summary.
- `study://<study>/records/<name>`: records a plugin's tools keep, including each
  record's producing branch.

The study id is the root question's id. Publishing a view's dashboard again with its
`report_id` revises it (the view shows the latest version); a new direction can have
its own view; `set_status` (`withdrawn`) withdraws one that no longer serves. A branch
may attach drill-down views of its own.
