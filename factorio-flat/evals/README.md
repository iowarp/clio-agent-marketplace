# Factorio Flat black-box evals

`behavioral-cases.json` contains user messages and semantic expectations. An
external adapter should send each message to an activated `factorio-flat`
session and normalize the public response, the observable tool trace, and the
runtime state that trace produced. Every field below is a real runtime shape;
all five keys are required, because a missing key is not an empty one and the
evaluator rejects a trace it cannot read rather than grading it as compliant.

```json
{
  "case_id": "case id",
  "response": "public assistant response",
  "actions": [
    {"name": "tool name", "arguments": {}, "result": {}}
  ],
  "tasks": [
    {
      "task_id": "agent task id",
      "agent": "child expert id",
      "child_session_id": "the child's session id",
      "status": "queued | running | completed | failed | cancelled",
      "error_reason": "typed reason, empty when none"
    }
  ],
  "questions": [
    {
      "id": "question id",
      "session_id": "session the row lives on",
      "owner_session_id": "session that asked (the CHILD, when forwarded)",
      "attended_session_id": "session the scientist is attending",
      "status": "pending | answered | cancelled | expired",
      "source": "orchestrator | child_forwarded",
      "prompt": "question text",
      "metadata": {}
    }
  ],
  "sessions": [
    {"session_id": "session id", "status": "status observed during the run"}
  ]
}
```

Action results keep their runtime shapes: `spawn_agent_task` returns one handle
(`task_id`, `status`, `run_index`, `queued_reason`), `spawn_agents_parallel`
returns those handles under `spawned`, `wait_agent_tasks` returns full-fidelity
rows under `results`, and `check_agent_tasks` returns compact rows under `tasks`.

There is no paused task status. A child that needs a scientist-owned decision
keeps status `running`; the runtime flips that child's session to `waiting_user`
and mints a forwarded question on the attended root whose `owner_session_id` is
the child session. The evaluator recognizes a blocked consultation by that
conjunction, attributing it to a task by joining the question's
`owner_session_id` to the task's `child_session_id`.

The evaluator never reads pack prompts and does not compare exact prose. It
checks response floors and ceilings, the capabilities a case genuinely needs,
question utility, fan-out width, the exact agents consulted, whether the
consulted children actually completed, whether the answer carries what they
returned, and blocked-child resume continuity. It asserts outcomes only: no
forbidden-tool lists, no call caps, and no required tool ordering. Evaluate a
captured result file with:

```powershell
uv run --no-project python scripts/evaluate_factorio_flat.py `
  factorio-flat/evals/behavioral-cases.json captured-results.json
```

The repository test fixture contains representative compliant traces plus
negative evaluator tests. It validates the grading contract in CI; replacing it
with traces from a deployed runtime provides live behavioral qualification.
