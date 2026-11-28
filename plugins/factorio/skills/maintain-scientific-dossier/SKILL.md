---
name: maintain-scientific-dossier
title: Maintain the Scientific Dossier
description: Keep research identity, evidence, assumptions, decisions and artifact status traceable across the conversation as entries of the study log, never as a separate prose record.
keywords:
- level:L1
- factorio
- provenance
---

The dossier is the study log: the research state lives as log entries
(`log_entry`, `set_status`, `link`, `query_log`), not as a file of prose.
`run-a-study` covers how entries and their links work.

Each entry holds one kind of knowledge: scientist-supplied fact, external
evidence, expert inference, proposed default, accepted decision, unresolved
question, or unverified artifact claim.

- **A consequential decision** is a Question (the decision to make, with its
  units and alternatives) answered by a Conclusion whose claims cite the evidence,
  with the rationale, owner and the assumptions and artifacts it affects in the
  claims and caveats. A correction is a new Conclusion; the old one gets
  `set_status` superseded with the reason and what must be revisited. History is
  never overwritten.
- **An assumption** is a Hypothesis with the prediction that would show it wrong;
  `set_status` records when it is supported, refuted or superseded.
- **Artifact status** (generated, statically reviewed, scientist-approved,
  solver-executed, validated) is an Observation that cites the call that produced
  or checked the artifact; each later check is another Observation, and the
  Evidence interpreting it says which status the artifact has reached.

A deliverable useful outside chat is a `create_artifact` call (runtime-provided)
with complete content, a workspace-relative name, and exact inputs in `used`.
The returned artifact identity and version name it; a rejected call created
nothing.
