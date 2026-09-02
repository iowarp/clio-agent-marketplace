# Factorio Flat black-box evals

`behavioral-cases.json` contains user messages and semantic expectations. An
external adapter should send each message to an activated `factorio-flat`
session and normalize the public response and observable tool trace as:

```json
{
  "case_id": "case id",
  "response": "public assistant response",
  "actions": [
    {
      "name": "tool name",
      "actor_task_id": "optional child identity",
      "arguments": {},
      "result": {}
    }
  ]
}
```

The evaluator never reads pack prompts and does not compare exact prose. It
checks response shape, tool choice, question utility, skill-before-delegation,
fan-out width, and blocked-child task continuity. Evaluate a captured result
file with:

```powershell
uv run --no-project python scripts/evaluate_factorio_flat.py `
  factorio-flat/evals/behavioral-cases.json captured-results.json
```

The repository test fixture contains representative compliant traces plus
negative evaluator tests. It validates the grading contract in CI; replacing it
with traces from a deployed runtime provides live behavioral qualification.
