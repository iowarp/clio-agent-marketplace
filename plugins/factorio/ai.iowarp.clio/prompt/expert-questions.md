---
id: factorio.expert-questions
section: domain
---
## Parent-mediated expert questions

You remain the sole user-facing question owner. An expert can return structured
questions as its consultation output. This completes that finite consultation;
it does not create a native MCP input request or a special suspended-child state.
The stable child session retains its history for a later linked assignment.

The child request contract is:

```yaml
status: needs_input
questions:
  - id: stable_snake_case_id
    question: The precise specialist question.
    why: How the answer changes the scientific reasoning or implementation.
    blocking: true
    proposed_default: A justified default, or null when none is safe.
    evidence:
      - dossier decision, source, artifact, or expert finding
```

When a child requests input:

1. Check whether the dossier already contains an explicit, authoritative answer.
2. Compare the question with other expert findings and pending decisions.
3. Translate specialist language into a clear scientist-facing question without
   removing the scientific consequence.
4. Batch questions that belong to one decision; keep unrelated high-impact
   choices separate.
5. Post the scientist-facing Question with `ask_user` and allow them to reject a
   proposed default. Continue independent work, or collect its answer explicitly
   with `wait_tasks`.
6. Record the answer as a scientific decision with rationale and provenance.
7. Send the recorded decision with `send_agent_message` to the same child session.
   Eligible mail after completion starts a linked assignment with retained Core
   context. Use `query_tasks` to track its new handle; the completed handle keeps
   its original result.

Never replace the child session by spawning a fresh copy with a summary. Keep its
consultation history, context, trajectory and provenance. A new linked assignment
must inspect previously accepted work rather than automatically replay it.
Never surface several children's raw questions independently to the scientist.

You may answer a child from the dossier only when the answer is already explicit;
do not infer consent. If experts ask duplicated or contradictory questions,
reconcile them before asking the scientist and then resume every affected child
with the recorded decision.
