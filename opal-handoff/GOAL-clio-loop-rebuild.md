# GOAL — clio agent-loop rebuild (approach B) to completion, tested and live-verified

This file is the grounding for a `/goal` run. It is self-contained: the machine may have been
wiped; everything needed is on pushed branches. Read this whole file, then
`opal-handoff/clio-loop-rebuild-plan.md` (the owner-approved plan) and
`opal-handoff/HANDOFF.md` on branch `wip/opal-handoff` of `iowarp/clio-agent-marketplace`.

## The goal
Rebuild clio-agent's agent loop per the approved plan (approach B): clio owns the loop as
`ClioReAct(dspy.Module)` on DSPy 3.4, clio-core is THE context system, providers are
stateful where they can be, tools run concurrently — and prove it: full test suite green,
live runs faster with equal answer quality, and the gact-tui web UI rendering every new
semantic correctly.

## Owner-settled principles (binding; do not re-litigate)
- Fail with a typed error rather than fall back. ONLY sanctioned fallback: the platform cannot
  run clio-core (not installable/present) → run on DSPy `History`, LOUD (typed degraded mode,
  UI + doctor). clio-core erroring or lost mid-turn → typed turn failure. Never switch mid-turn.
- clio-core keeps EVERYTHING as recorded events with role + actor (turns, summaries, injections,
  edit ops, fixes, hook effects). Two projections over one log: UI (everything visible) and
  agent-context (what the model sees) — they may differ.
- Context default = append-only, maximize prefix reuse. Edits are first-class recorded ops
  (today: compaction; soon: algorithm + human add/remove). Injections (plan reminder, todos,
  replan, task results, memory hits, files) are recorded once at the prefix edge and stay until
  an op removes them; the UI shows them.
- Deterministic fixes (arg repair, path grounding, circuit breaker, observation composition):
  each a config switch; each firing recorded, shown in the UI, AND told to the model next to the
  tool result.
- Provider sessions survive across turns; reset only on a recorded op or provider error (typed).
- Step = thinking (provider payload, byte-exact) · text (what `next_thought` really is; optional
  with tool calls, required on the final step = the answer) · tool calls → results.
- `dspy extract` = literally DSPy's extract, config-driven (steps > N, default 3, can disable);
  record an explicit amendment to `docs/design/react-loop-completion-2026-09.md`.
- Codex SDK / Claude Code SDK are LLM providers only (no dynamicTools, no SDK tool loop); the
  same code runs above the transport as for vLLM. SDK transports keep the text protocol (they
  take one prompt string, no tools); native tool calls only on direct APIs.
- Keep DSPy (signatures, adapters, LM layer, BestOfN/Refine, optimizers, module composition).
  Public DSPy API only; no hash pins on DSPy internals.

## Verified DSPy 3.4.0 facts (spike, installed code)
- Stock `ReActV2`: history stores only inputs/`next_thought`/`tool_calls`; tools sequential;
  no tool call → forced `submit` (clio's contract forbids) → do NOT use its loop.
- Text mode: after call 0, calls are append-only beneath ONE byte-identical trailing message
  (tools + "Respond with…"); `stateful_common.classify_delta` handles it.
- Native FC silently falls back to text when the LM lacks `supports_function_calling`
  (`adapters/base.py`) → clio chooses the mode from transport capability and fails on mismatch.
- With native reasoning, `dspy.Reasoning` forces `reasoning_effort="low"` and drops the step's
  visible text → ClioReAct owns its step signature and sets thinking explicitly.
- Custom LMs via `forward/aforward` and `messages=` dicts are deprecated (removed in 3.5) →
  migrate clio's custom transports to the Engine API (`complete(Request) -> Response`).

## Where things are
- clio-agent (github.com/iowarp/clio-agent), base `develop`. Phase 1 DONE (unit-tested, not yet
  fully suite/live verified): branch `feat/codex-sdk-stateful` (commit c5281076).
- Other pushed branches from the OPAL work (not merged; keep them, rebase when needed):
  clio-agent `feat/artifact-table-query`, `docs/chart-presentation-skill`,
  `docs/author-agent-pack-skill`; clio-schemas `feat/chart-kernel`; gact-tui `feat/chart-kernel`;
  clio-agent-marketplace `feat/appl-core-pack` (APPL-CORE blueprint), `feat/skill-literal-lint`,
  `wip/opal-handoff` (this material).
- Live harness: `opal-handoff/live/serve.sh` + `drive.py` (isolated instance, `CLIO_USER_DIR`
  set, Codex SDK). Baseline evidence: `opal-handoff/live/runs/exp67-first-contact`.
- OPAL dataset (exp67) lives outside git (owner's data); if absent, ask the owner for its path.

## Work — phases (each its own branch off develop, in a worktree; detail sub-plan at start)
0. Environment: fresh clones/worktrees, `uv sync --extra dev`, clio-core daemon working (the full
   suite needs it), Codex SDK signed in (`codex login`), gact-tui built (web). Rebase
   `feat/codex-sdk-stateful` on current develop.
1. Codex SDK stateful transport — finish: full suite green; live-verify (below).
2. `ClioReAct` + concurrent tools + cancellation at every step boundary; differential test vs
   stock `dspy.ReActV2` (byte-compare messages sent, documented deviations only); delete the
   ReActV2 subclass/`instrumented_forward` copy, `reactv2_upstream.py` pins, adapter class-name
   spoof, async-tool ban, dead `trajectory`/`tools_called` reads, workflow-era leftovers
   (`workflow_state` auto-inject, prose-parsed prior state, routing fields, planner LM, EarthScope
   trace), the DSPy-history read fallback, the streamed→sync second run. Drop the per-executor
   MCP call lock; make observer/gate state per call.
3. clio-core as the context system: event vocabulary on the `_events` family; agent-context
   projection spanning turns (earlier turns as real messages — delete the prose blob in
   `session_store._compile_session_conversation_history`; no per-turn working-set wipe);
   injections/steers/child results as events in their own role at the step boundary (not glued
   onto observations); compaction summarizes what clio-core holds (failing-first test for the
   suspected mid-turn loss); thinking payloads stored byte-exact; UI projection shows
   injections/edits/fixes; the loud platform fallback + typed failure otherwise.
4. Fixes + hooks as recorded, configurable events (each fix a `conf.resolve` switch documented via
   `scripts/gen_env_reference.py`; firing recorded + UI-visible + told to the model; hook effects
   recorded). Ask the owner for fix defaults.
5. DSPy 3.4 upgrade (Engine API transports) + thinking pass-back per provider (Anthropic signed
   blocks, OpenAI/Codex encrypted items, Gemini signatures, raw for open models) + native tool calls
   on direct transports + Codex direct stateful chain (`previous_response_id`) — ask the owner to
   log in to Codex direct when reached.
6. Config-driven `dspy extract` (+ contract amendment); relay onto MCP tasks per
   `docs/design/mcp-client-unification-2026-08.md` campaign 2 (only if time; ask owner).

## Definition of done (all must hold)
1. clio-agent full suite green on every phase branch: `pytest tests -m "not integration"` —
   zero failures, zero errors; skips only the documented platform/live-gated ones. ruff, ruff
   format, mypy, `scripts/check_file_size.py`, `scripts/check_silent_fallbacks.py`,
   `scripts/gen_env_reference.py --check` all pass. Failing-first tests for every bug fixed.
2. New tests: ClioReAct differential test; projection prefix-stability test (render(n) is a
   prefix of render(n+1) unless an op landed); UI-vs-agent projection test; fix-recorded-and-told
   test; Codex stateful tests (exist).
3. Live (isolated instance, Codex SDK, realistic short human prompts via `drive.py`):
   `"<exp67 path> what is this data?"`, `"does the nickel hurt growth?"`,
   `"show me the growth curves"`. Baseline: 39 / 7 / 5 min, 79 steps, 9.87M input tokens.
   Report per turn: wall time, steps, input/cached/output tokens, full vs delta sends, one thread
   per conversation. Must be clearly faster with high cached share, and answer quality unchanged
   (still catches: DBL_MAX sentinel, ghost string band columns, unflagged empty rows, RGB2 mm
   scale, canopy clipping, MSC1 invalid source).
4. gact-tui web UI verified in a real browser (drive it; screenshots/GIF): thinking streams live;
   tool calls + results render (concurrent calls too); injections, compaction checkpoints, edits
   and fixes are visible as such; a mid-turn steer lands as a user message; cancel stops a running
   turn promptly; reload == live; multi-turn follow-up reuses prior context without re-sending.
5. Obsidian/clio-agent docs updated to describe what IS (design doc for the loop + context
   projection in `docs/design/`), stale docs fixed (`docs/providers/claude_code.md`,
   `docs/tui/08-semantics-and-lifecycle.md`).

## Rules
- Branches off `develop` in worktrees; COMMIT AND PUSH AFTER EVERY COHERENT STEP; never merge to
  develop/main or open PRs until the owner says. Conventional commits; NO Claude/Co-Authored-By
  attribution line.
- Read before changing: the relevant `docs/design/*` and the code path; separate DOES vs SHOULD.
- No silent fallbacks, no new deterministic decision-making on model prose, no accretion into
  god files (owner modules), no ratchet raises.
- Ask the owner (don't guess) for: Codex direct login, fix defaults, whether `next_thought` is
  required only for non-thinking models, merge/PR timing, anything that contradicts this file.
