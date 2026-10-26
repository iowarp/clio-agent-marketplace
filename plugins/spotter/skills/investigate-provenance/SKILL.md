---
name: investigate-provenance
title: Investigate Provenance
description: Start each review from review_activity, then answer an execution or artifact-lineage question in depth from the configured provenance stores (Flowcept, CMF or CLIO's native journal) with the spotter tools - discover what the active providers can answer, move from summaries to exact tasks and lineage graphs, join the two sides through a correlation id, and report coverage honestly. Load when a wake or a question needs evidence of what the watched session ran or produced.
keywords:
- level:L0
- provenance
- lineage
---

# Investigate provenance

## Start from the review loop

Every review starts with `review_activity` (pass the previous `next_since` as
`since`). It returns the watched session's requests, answers, tool calls with
their inputs and outputs, writes and model calls, so you can compare what was
asked with what was done before opening any store. Use `attention_sources` on
an exact quoted passage when you need to know what steered an answer or an
action (see `inspect-attention`). Reach for the provenance tools below for a
deep dive: an id to resolve, a lineage to verify, a gap to explain.

## The provenance stores

The `spotter` tools read the provenance stores CLIO's configuration names. Which
store answers is configuration, never a tool argument: no tool takes a provider
name, and you never claim one provider was queried when another is configured.

## Start with capabilities

Begin an unfamiliar investigation with `spotter_capabilities`. It names the
active agentic (execution) provider and artifact provider, their health, how the
query lane was chosen, any enabled provider that is not queried, and the exact
operations each side can answer. Every query result repeats its `lane`; read it.
A `lane_defaulted` hint means the native journal answered while another provider
is enabled: say so rather than reporting an empty result as "nothing happened".

## Execution questions

Move from campaign to workflow to task evidence:

1. orient with `spotter_list_campaigns`, `spotter_list_workflows` and
   `spotter_summarize_tasks` (status, activity, duration and time range);
2. narrow with `spotter_query_tasks` (workflow, task, agent, status, activity or
   subtype filters) and `spotter_list_agents`;
3. read order and dependency with `spotter_get_timeline` for one workflow.

## Artifact questions

Move from pipeline and stage inventory to executions or artifacts, then to the
lineage graph:

1. `spotter_list_pipelines`, `spotter_list_executions`,
   `spotter_list_artifact_types`, `spotter_list_artifacts`;
2. `spotter_get_execution_lineage` for what one execution read and wrote, or
   `spotter_get_artifact_lineage` for where one artifact came from;
3. `spotter_get_model_card` for a recorded model's execution, inputs and outputs.

Artifact tools are served only when the configured artifact provider answers
them, so a tool missing from your list is a capability boundary; a missing
artifact capability is not proof that no lineage exists.

## Joining the two sides

`spotter_trace_correlation` connects an agentic action to an artifact execution
through an exact CLIO correlation id. Report both provider sides, and name any
side without a match.

## What a deviation looks like

Compare what the session was asked to do (`review_activity`) with what the
stores recorded:

- a write or artifact with no request or task behind it;
- an output whose recorded inputs differ from the inputs it claims;
- a task that ran after an untrusted input (a fetched page, a file, a tool
  result) and departs from the person's request;
- a workflow, agent or tool that appears in the record but not in the
  conversation.

Each is a question to resolve with evidence, not a verdict.

## Reporting

- Quote stable ids (workflow, task, execution, artifact, correlation) and the
  provider that returned them.
- Distinguish recorded facts from inference.
- `capability_unavailable` is a real boundary: name the provider lacking the
  operation and the evidence that would be required. There is no fallback.
- Report truncation (a result at its `limit`), provider unavailability and
  incomplete graphs explicitly.
