# APPL-CORE Analyst black-box evals

`behavioral-cases.json` holds user messages and semantic expectations for an
activated `appl-core` session. Each case names the bundle it runs against
(`bundle`: `primary`, or `variant:<name>` for a mutated copy made by
`scripts/make_variants.py`) and its preconditions (for example "no `.clio`
directory" or "a current card from `first_contact_onboarding`"). The adapter
substitutes `{bundle_root}` in `user_message` with the bundle's absolute path.

## Producing traces

For each case, an external adapter:

1. prepares the bundle root as the preconditions say (delete or keep
   `<bundle_root>/.clio/`; start a fresh session when the case says so);
2. sends `user_message` to the session and waits for the turn to end;
3. writes one normalized record per case:

```json
{
  "case_id": "case id",
  "response": "public assistant response",
  "actions": [{"name": "tool name", "arguments": {}, "result": {}}],
  "tasks": [{"task_id": "...", "agent": "...", "child_session_id": "...", "status": "completed", "output": "..."}],
  "questions": [{"id": "...", "status": "pending", "source": "orchestrator", "prompt": "..."}],
  "sessions": [{"session_id": "...", "status": "..."}],
  "bundle": {
    "card_text": "contents of <bundle_root>/.clio/experiment-card.md after the turn, or null",
    "view_hash_runs": [{"<view path>": "<sha256>"}],
    "verify_exit_codes": [0],
    "files_written": ["paths the turn created or changed under the bundle root"]
  }
}
```

`tasks`, `questions`, and `sessions` keep the runtime shapes described in
`factorio-flat/evals/README.md`. `bundle.view_hash_runs` has one entry per
loader run observed in the trace (the adapter hashes `.clio/views/` after
each `loader.py` shell action, or reads the `card.py record/verify` output);
`verify_exit_codes` holds the exit status of each `card.py verify` call.

Every top-level key is required; the grader rejects a trace it cannot read
instead of grading it as compliant.

## What the cases assert

- **First contact** (`first_contact_onboarding`, `first_contact_delegated`):
  the export skill, onboarding, and evidence skills were used; the bundled
  audit scripts ran; the card exists with tagged claims, open questions, and
  `[trap:<class>]` lines covering the trap classes known for the primary
  export; the loader is deterministic and `card.py verify` passed. The
  delegated case also requires that the parent re-ran the child's loader
  *after* collecting it.
- **Card reuse** (`card_reuse_second_session`): with a current card, no
  profiling script runs; the card is verified instead.
- **Loader determinism**: two loader runs give identical view hashes.
- **Ask, do not assume** (`ask_treatment_meaning`, `ask_unit_scale`): the
  agent puts a question to the user about the treatment's meaning/unit or a
  suspicious size scale.
- **Version refusal** (`refuse_export_v7`): no views are written and the
  response names the export version.
- **Held-out variants**: categorical treatment, unbalanced design, sentinel
  moved to another table, dropped modality, renamed columns -- each onboarded
  with the matching trap class recorded and a verified loader.
- **One question per L1 skill**: the matching skill was loaded.

It asserts outcomes only: no tool-order requirements beyond "re-run after
collecting the child", no call caps, no forbidden-tool lists.

Limits, stated plainly: `terms_any` checks are a lexical floor; trap classes
prove the agent recorded a trap of that class, not that the line is correct
(a reader compares the card with the known trap list); the expected trap
classes for `primary` come from the local test export, so re-derive them for
another primary export.

## Making variants

```powershell
uv run --no-project --with "pyarrow>=15" python appl-core/evals/scripts/make_variants.py `
  SRC_BUNDLE OUT_DIR --variant export_v7 --seed 0
```

Variants copy tables, manifest, and docs only (asset directories are skipped,
or symlinked with `--link-assets`), never copy `.clio/`, and never write into
the source bundle. The provenance record goes to `OUT_DIR.variant.json`,
outside the variant, so the agent under test cannot read it.

## Grading

```powershell
uv run --no-project python appl-core/evals/scripts/evaluate_appl_core.py `
  appl-core/evals/behavioral-cases.json captured-results.json
```

The pack's tests validate the grader against hand-written traces (compliant
and non-compliant). Live qualification needs traces from real sessions.
