---
name: run-a-study
title: Run a branched study
description: Run a study in the study log: a question, competing hypotheses with refuting predictions, branches that test them in parallel as a workflow, observations that cite their calls, evidence from your own analysis, forks when a branch finds something new, and a merged conclusion whose every claim cites entries.
keywords:
- method
- study
- hypotheses
- workflow
---

# Run a branched study

The log records what was learned; the workflow runs the work. The log never judges a
claim: you choose the analysis, you decide what is enough, and you say why.

## Frame it

1. Write the question with `log_entry` (`type: question`): the statement and its
   scope. If the person gave a limit on what the study may spend, put it on this root
   question as `budget` (amount and unit); every Observation then states its `cost`.
2. Write one Hypothesis per competing answer (`links: {question: <id>}`), each with
   the `refuting_prediction` that would show it wrong. When a hypothesis states a law,
   give it as `formula` too.

## Branch it

3. Run the study as a workflow with `run_workflow`, started with `isolate: true` so
   each step writes in its own folder: one step per hypothesis with target `self`,
   a merge step after them, and `review` as an editor. Each step's task names its
   hypothesis id and asks it to design and run the test.
4. In a branch, write the Experiment first (`links: {hypothesis: <id>}`): the method
   and the sample size you intend. Form your own design before reading what other
   branches found. Spread the work across children when it is separable.

## Record what happened

5. Log every run as an Observation (`links: {experiment: <id>}`). In `from_calls`,
   cite the recorded calls that produced it: every tool result carries its `call:`
   reference. Put the values in `measurements` with their `conditions` (settings,
   seed, strategy, node, repeat index). When a tool returned the value, name it with
   `source: {call, field}` instead of typing it. If your own script writes a result
   file, designate it as an artifact so its hash is on record.
6. Before claiming anything, read the other branches with `query_log`. Say in your
   Evidence when you relied on another branch's result.
7. Analyze in your own code. `export_measurements` writes the measurements to a data
   file with a manifest; run the analysis the experiment needs (a mean, a paired
   comparison over shared conditions, an interval, a fitted model), record its seed
   when it is random, and cite that analysis call as `analysis_call` in the Evidence
   (`links: {observation: [...], supports | refutes: <hypothesis>}`). Give `strength`
   honestly, and say so when the sample is too small to separate two hypotheses.
   Record a hypothesis's fate with `set_status` (supported, refuted, superseded) and
   the reason.

## Change course

8. When a branch finds a new hypothesis, write it, then `fork` with a note naming
   it: the fork carries your conversation and pursues the new direction beside you,
   and the merge waits on it.
9. When the question itself should change, write the new Question and a Reframe
   (`links: {old_question, new_question, evidence}`), then fork with a note naming the
   new question.

## Close it

10. The merge step reads every branch's entries and writes one Conclusion
    (`links: {question: <root id>, merges: [...]}`): each claim cites the entries it
    rests on, a quantitative claim cites its analysis call, `confidence` and
    `caveats` are explicit, and `relation` says whether it answers the question,
    refutes its premise or replaces it. Record a Conflict for each disagreement
    between branches you do not resolve, citing both sides.
11. Show the comparison as a chart from the measurements, not as prose alone.
