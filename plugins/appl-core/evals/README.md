# APPL-CORE Analyst acceptance cases

These cases assess whether an agent can investigate messy, read-only data and
answer the question using evidence. They do not prescribe a loader, five table
shapes, a card filename, a sequence of scripts or a cleaned source copy.
`behavioral-cases.json` contains ordinary requests and operator-only expectations.
Keep expected answers, variant provenance and evaluator records outside the
agent's accessible inputs.

## Source and environment

Expose the source through verified read-only access. A writable test copy is not
the demo contract: use the actual source-access policy or a read-only mount and
retain its access receipt. Put the workspace state and output directory elsewhere.
Do not repair the source between turns to let a fixed pipeline pass.

Held-out variants can be created by an operator with `scripts/make_variants.py`.
It writes a separate fixture, never the original bundle. Expose that fixture
read-only to the tested agent as well. Variants change columns, modalities, factor
encodings, balance, sentinels and version metadata. The unavailable-helper case
also changes an environment assumption while retaining an accessible data reader.
The agent must inspect and adapt, not receive an answer key or required repair.

## Observer record

An adapter records actual tool actions, task/question states, source access and
artifact evidence. This JSON is an **evaluation trace format**, not a schema the
dataset or agent-produced tables must follow. Do not ask the model to manufacture
it. The adapter must collect the underlying receipts and file fingerprints.

```json
{
  "case_id": "first_contact_onboarding",
  "response": "actual public response",
  "actions": [{"id": "call_1", "name": "actual tool", "arguments": {}, "result": {}}],
  "tasks": [],
  "questions": [],
  "sessions": [],
  "bundle": {
    "source_access": {"mode": "read_only", "verified": true, "receipt": "operator access receipt"},
    "source_hashes_before": {"relative source path": "64-character lowercase SHA-256"},
    "source_hashes_after": {"relative source path": "same SHA-256"},
    "source_writes": [],
    "inspected_sources": ["relative source path"],
    "findings": [{"description": "observed finding", "evidence": ["relative source path", "call_1"]}],
    "adaptations": [{"description": "observed obstacle and adjusted approach", "evidence": ["call_1"]}]
  }
}
```

Hash the source independently before and after, preserving the same file scope
and detecting additions and removals. `source_writes` records successful source
mutations observed during the run, including changes later restored. A final
matching checksum alone cannot conceal such a write. The access receipt must
verify the actual read-only policy, not merely repeat an agent claim.

Findings and adaptations reference inspected source paths or actual action IDs.
An absent loader, card or view is valid when the question did not need one.
Optional `card_text`, `view_hash_runs` and `verify_exit_codes` remain readable for
historical traces and the explicitly requested reproducibility case. No current
onboarding case requires `card.py verify`, a particular script or a fixed schema.

## Acceptance

- Source remains unchanged and actual read-only access is verified.
- The agent inspects the supplied data and gives source-backed findings. Human
  review checks whether those findings and the answer are correct, not merely
whether the prose mentions a list of terms.
  Status receipts, pending audits and unrelated manifest/README references do not
  support scientific findings. Review the cited content and calculation, not
  merely whether a reference exists. Natural prose is accepted without claim tags.
- Unknown or missing versions lead to inspection and qualified use of readable
  evidence. Only a specific inaccessible or uninterpretable part can be blocked.
- Changed columns, incomplete modalities and an unavailable helper lead to a
  justified adjusted approach, without rewriting the source or inventing units.
- Questions about uncertain treatment meaning, units or calibration remain
  explicit. Independent work can continue while an answer is pending.
- Delegated work returns actual evidence that the parent checks. No mandatory
  repeat of an entire child pipeline is imposed.
- The separate reproducibility request compares two runs because that user
  specifically requested it. It is not a prerequisite for every analysis.

`method_skills` labels case coverage for maintainers; it does not require a
particular skill-load action. A direct query, a different reader or task-specific
code can satisfy the same outcome. The bundled five schemas remain optional
examples, not acceptance gates.

## Grading and limits

```text
uv run --no-project python plugins/appl-core/evals/scripts/evaluate_appl_core.py plugins/appl-core/evals/behavioral-cases.json captured-results.json
```

The grader rejects missing preservation evidence, changed inputs, source writes,
unsupported evidence references and missing observed adaptations. Lexical and
record-shape checks are only a mechanical floor. They do not establish scientific
correctness or fresh live acceptance. Retain source/tool receipts and review the
actual findings, calculations, limitations and interactive outputs.

Unit cases use synthetic traces to exercise the grader. They are not a live
model run or qualification of a real OPAL export. Do not rerun infrastructure or
substitute another provider to manufacture that evidence.
