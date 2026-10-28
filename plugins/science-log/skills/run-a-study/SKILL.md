---
name: run-a-study
title: Run a branched study
description: "Run a study in the study log: a question, competing hypotheses with refuting predictions, branches that test them in parallel as a workflow, observations that cite their calls, evidence from your own analysis, forks when a branch finds something new, and a merged conclusion whose every claim cites entries."
keywords:
- method
- study
- hypotheses
- workflow
---

# Run a branched study

The log records what was learned; the workflow runs the work. The log never judges a
claim: you choose the analysis, you decide what is enough, and you say why. The log is
the study's record: the person reads the study in its Science log, follows each claim
to the entries and calls behind it, and can export the measurements. Your final answer
summarizes the Conclusion; a result that is only in your answer cannot be checked.

## Frame it

1. Write the question with `log_entry` (`type: question`): the statement and its
   scope. If the person gave a limit on what the study may spend, put it on this root
   question as `budget` (amount and unit); every Observation then states its `cost`.
2. Write one Hypothesis per competing answer (`links: {question: <id>}`), each with
   the `refuting_prediction` that would show it wrong. When a hypothesis states a law,
   give it as `formula` too, written `<measured> = <expression>` in the names the
   data use (the apparatus's inputs, a table's columns), with numbers, `+ - * / ^`,
   parentheses, `pi` and `sqrt exp log abs min max`; a threshold is a `max` or `min`.
   A formula in the data's own names can be drawn against every reading.
3. Size the study from the claims it must support. A claim that one approach beats
   another needs each approach tried under shared conditions (the same inputs, seeds
   or settings), often enough that the difference stands out from the run-to-run
   spread; a single trial supports neither. Estimate that spread first (a short pilot
   or the first trials): a sample whose interval stays wider than the difference worth
   reporting cannot decide between the hypotheses, so when nothing limits the study,
   enlarge it rather than conclude. A claim about a law needs measurements across the
   range it covers. Write the intended sample size on each Experiment; a sample too
   large for one conversation is work to spread across children (step 5).

## Branch it

4. Run the study as a workflow with `run_workflow`, started with `isolate: true` so
   each step writes in its own folder: one step per hypothesis with target `self`,
   a merge step after them, and `review` named in `editors`. An editor acts when a
   step fails, or when it runs as a step: put a step targeting `review` after the
   merge to read its result and, when the evidence cannot decide, add the steps
   that would (a larger sample, a new condition) and a merge after them. Each step's
   task names its hypothesis id and asks it to design, run and analyze the test. The
   branch is where a result no hypothesis offered is first seen and pursued (steps 9
   and 10); a branch told only to gather data and report it back has no results of
   its own to change course from.
5. In a branch, write the Experiment first (`links: {hypothesis: <id>}`): the method
   and the sample size you intend. Form your own design before reading what other
   branches found. Independent trials are separable work: spread them across
   children (each a self-contained batch with its conditions and the Observations to
   log), so each child's context holds only its own trials and yours holds their
   results, and the batches run side by side.

## Record what happened

6. Log every run as an Observation (`links: {experiment: <id>}`). In `from_calls`,
   cite the recorded calls that produced it: every tool result carries its `call:`
   reference. Put the values in `measurements` with their `conditions` (settings,
   seed, strategy, node, repeat index). When a tool returned the value, name it with
   `source: {call, field}` instead of typing it. If your own script writes a result
   file, designate it as an artifact so its hash is on record.
7. Before claiming anything, read the other branches with `query_log`. Say in your
   Evidence when you relied on another branch's result.
8. Analyze in your own code. `export_measurements` writes the measurements to a data
   file with a manifest; run the analysis the experiment needs (a mean, a paired
   comparison over shared conditions, an interval, a fitted model), record its seed
   when it is random, and cite that analysis call as `analysis_call` in the Evidence
   (`links: {observation: [...], supports | refutes: <hypothesis>}`). Give `strength`
   honestly, and say so when the sample is too small to separate two hypotheses.
   Record a hypothesis's fate with `set_status` (supported, refuted, superseded) and
   the reason. A branch analyzes its own results before it ends, even when the merge
   will compare all of them.

## Change course

9. When your results suggest an explanation no hypothesis offered (a pattern, an
   outlier, a cause), that is a new hypothesis: write it, then `fork` with a note
   naming it. The fork carries your conversation and pursues the new direction
   beside you, and the merge waits on it.
10. When the question itself should change (its premise is false, or each answer
   holds only under conditions the question did not name), write the new Question
   and a Reframe (`links: {old_question, new_question, evidence}`). In a workflow,
   fork with a note naming the new question; otherwise carry on with it. The
   Conclusion answers the question the study ended with.

## Close it

11. The merge step reads every branch's entries and writes one Conclusion
    (`links: {question: <root id>, merges: [...]}`): each claim cites the entries it
    rests on, a quantitative claim cites its analysis call, `confidence` and
    `caveats` are explicit, and `relation` says whether it answers the question,
    refutes its premise or replaces it. Record a Conflict for each disagreement
    you do not resolve, citing both sides: between branches, or between two results
    (a measurement and a calculation, two methods) that should agree.
12. Show the comparison as a chart from the measurements, not as prose alone.

## Views

A study's views are where the scientist watches it run and checks its conclusion.
They are your dashboards, built around the question: what would show whether a
hypothesis holds, how the branches compare, where the study is now. Make one with
`create_a2ui_surface` and attach it with `log_entry` (`type: view`, its `surface_id`,
a `title`, the `purpose` it serves, `links: {serves: <question or hypothesis>}`).

A chart or table in a view can read the study directly, and it shows new entries as
they arrive without you rebuilding it:

- `study://<study>/measurements`: every measured value with its conditions, branch
  and status; when a standing hypothesis gives a `formula` in the data's own names,
  each row also carries the law's prediction (`law_value`) and the law (`law`).
- `study://<study>/entries`: every entry with its type, branch, status and summary.
- `study://<study>/records/<name>`: records a plugin's tools keep (for example a
  game's board or a bench's readings), by branch.

The study id is the root question's id. Revise a view's surface as the study changes
course, and add a view when it takes a new direction; withdraw one that no longer
serves with `set_status` (`withdrawn`). A branch may attach drill-down views of its
own.
