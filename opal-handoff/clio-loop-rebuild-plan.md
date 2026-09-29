# Plan: clio agent loop rebuild (approach B on DSPy 3.4) — fast, clio-core as the context system

## Context
A live OPAL run over the Codex SDK took 39 min for one question (79 serial steps, 9.87M input tokens / 93k out).
Root causes (all code-verified):
1. **Full resend every step.** The Codex SDK transport opens an ephemeral thread per LM call and sends the whole
   history as one prompt (`providers/codex/sdk_client.py:450-473`). v0.7.0 had a Codex stateful delta
   (2.95s vs 7.37s TTFT, 76.7% cached); the Aug-2026 SDK rework removed it.
2. **Serial tools.** One `asyncio.Lock` per MCP executor held for the whole call; the executor is shared per
   workspace (parent + children serialize); DSPy's loop runs calls one by one.
3. **Context rebuilt per turn, not projected.** Each turn recomposes the system prompt, re-inlines files, renders
   prior turns as prose inside the user message, and wipes the working set → no cross-turn prefix reuse.

The deeper finding: clio already runs its own loop (`instrumented_forward` is a modified copy of ReActV2's, with
hash pins on code it doesn't run), and clio-core (ARC) is ~80% a context engine but the agent's context is still
assembled by string concatenation. The owner's decision: **approach B** — clio owns the loop as a DSPy module on
DSPy 3.4, clio-core is THE context system, performance first.

## Owner-settled principles
- Fail with a typed error rather than fall back. The ONLY fallback: the platform cannot run clio-core
  (not installable / not present) → run on DSPy `History`, LOUD (typed degraded mode, UI + doctor).
  clio-core erroring or lost mid-turn → typed turn failure. Never a silent or mid-turn switch.
- clio-core keeps everything (every turn, summary, injection, edit, fix) as recorded events with role + actor.
  Separate projections: UI (everything visible) and agent-context (what the model sees) — may differ.
- Context edits today: only compaction (manual/auto). Future (~3 months): algorithms + humans add/remove context
  → edits are first-class recorded ops. Default: append-only, maximize prefix reuse.
- Injections (plan reminder, todo recitation, replan, task results, memory hits, files) = recorded additions at
  the prefix edge; recorded once and stay in context until an op removes them; the UI shows them.
- Deterministic fixes (arg repair, path grounding, circuit breaker, observation composition): each a config
  switch; each firing recorded, shown in the UI, AND told to the model next to the tool result.
- Provider sessions survive across turns; reset only on a recorded op or provider error (typed).
- Step = thinking (provider) · text (what `next_thought` really is; optional with tool calls, required on the
  final step = the answer) · tool calls → results.
- `dspy extract`: literally DSPy's extract, config-driven (steps > N, default 3, can disable); amend the
  react-loop-completion contract explicitly.
- Codex/Claude SDKs are LLM providers only; identical code above the transport for every provider.
- Keep DSPy for semantics, optimizers, BestOfN/Refine, module composition (subagents/surrogate modules).
- Rules: branches off `develop` in worktrees under `D:\Libraries\Documents\projects\opal-work\`; no merge/push
  until the owner says; conventional commits, no AI attribution; failing-first tests; ruff/mypy; no ratchet raises.

## Design (B on DSPy 3.4)
- **D1 clio-core event log + projections.** Events: user message · injection (actor=algorithm) · steer · model
  step (complete provider response incl. thinking payload) · tool result (raw + model-facing) · child result ·
  compaction checkpoint · edit op (actor=human|algorithm) · fix fired · hook effect. Agent-context projection =
  one function per agent scope, spanning turns, append-only by default, ops applied. UI projection = the same log
  with everything visible. Built on the existing `_events` family (`arc/working_set_fold.py`, part atoms) —
  no fifth store.
- **D2 `ClioReAct(dspy.Module)`**, stateless, per step: boundary (cancel? apply new events) → context =
  project(clio-core) → `dspy.Predict` → record the complete step → run tool calls concurrently → record results →
  end (no tool call = answer · submit · ask_user/plan_exit yield · optional extract). Public DSPy API only;
  differential test vs stock `dspy.ReActV2`. Hooks (BeforeModel/AfterModel/PreToolUse/PostToolUse/Stop) applied
  at fixed step points, their effects recorded.
- **D3 Transport contract.** Prefix-stable rendering (render(log[0..n]) is a prefix of render(log[0..n+1]) unless
  an op landed). Stateful where the provider is (Codex thread, Claude session, Responses `previous_response_id`),
  prefix-cached where stateless. Thinking stored byte-exact and sent back in provider format. Native tool calls
  on direct APIs; text protocol on the SDK transports (they accept one prompt string, no tools).

## Build phases (each = own branch/worktree off develop; phases 2+ get a detailed sub-plan when they start)

### Phase 0 — DSPy 3.4 spike (throwaway worktree `opal-work/clio-agent-dspy34`, branch `chore/dspy-3.4-eval`)
Install `dspy==3.4.0` in the worktree venv; with a scripted LM confirm against real code: `dspy.Predict` with a
`dspy.History` input (message layout, the trailing "Respond with…" reminder), `ChatAdapter` text mode vs
`use_native_function_calling=True`, async `acall`, streaming listeners, `ReActV2` message sequence (for the
differential test), breaking changes vs 3.3.0b1 (`BaseLM.forward`, `Image.from_path`, `dspy.LMRequest`).
Deliverable: a short findings note in the Obsidian doc; no production code.

### Phase 1 — Codex SDK stateful transport (branch `feat/codex-sdk-stateful`)
Adapter-only change; nothing above the transport changes.
- **Measure first.** Carry cached input tokens through (captured `sdk_client.py:267`, dropped at `:197-209`,
  `sdk_transport.py:184-206`, `:300-307`) as `prompt_tokens_details.cached_tokens` (read by `gact/usage.py:61`);
  per-call timing + full-vs-delta counters in `runtime/turn_lm_ledger.py`.
- **One thread per session key.** Reuse `providers/stateful_common.py` (`classify_delta` — tolerates DSPy's
  moving reminder as a static tail; `StatefulSessionRegistry`; typed `STATEFUL_RESET_REASONS`). Generalize the
  handle to a server-minted Codex thread id. First call: `thread_start(...)` + full prompt, keep the `AsyncThread`;
  later calls: append-only → `thread.turn(delta)` on the same thread (verified: `AsyncThread` runs one or more
  turns, `openai_codex/api.py:680-771`); otherwise typed reset (new thread, full send).
- **Session key spans turns**: `(gact session, agent scope, model, cwd, effort)` instead of the per-forward
  uuid (`reactv2.py:292`). Until Phase 3 makes cross-turn context append-only, turn boundaries will reset typed
  (`prefix_mismatch`); within-turn deltas land now.
- **Codex auto-compaction off** for these threads (config override; verify key against the SDK config schema),
  or treat `thread/compacted` as a typed reset — Codex must never compact behind clio-core.
- Keep the SDK's single cancel path (`register_sdk_stream`), the bare-LM feature lockout, and the process-wide
  client; profile whether one client serializes parallel scopes.
- Delta rendering = the same `messages_to_prompt` JSONL serializer applied to the new messages only.
- Tests (unit): first call full; append-only call → same thread id, delta only; rewritten history → new thread
  + typed reason; respawn → `session_evicted`; moving reminder tolerated; cached tokens reported; Claude stateful
  tests still green. Full suite in the worktree `.venv` (`.venv\Scripts\python.exe -m pytest`), no failures/skips.

### Phase 2 — `ClioReAct` + concurrency + cancellation (branch `feat/clio-react`)
Replace `_RetainingReActV2`/`instrumented_forward` with `ClioReAct(dspy.Module)` honoring the replacement-loop
contract (Prediction shapes, per-step/per-forward side effects, typed error propagation, yields); differential
test vs stock ReActV2; concurrent tool calls per step (drop the per-executor call lock, make observer/gate state
per-call instead of thread-local); cancel checked at every step boundary. Delete: ReActV2 subclass overrides,
`reactv2_upstream.py` pins, adapter class-name spoof, async-tool ban, dead `trajectory`/`tools_called` reads,
workflow-era leftovers (`workflow_state` auto-inject, prose-parsed prior state, routing fields, planner LM,
EarthScope trace), the DSPy-history read fallback and the streamed→sync second run.

### Phase 3 — clio-core as the context system (branch `feat/context-projection`)
Event vocabulary (D1) on the `_events` family; agent-context projection spanning turns (earlier turns as real
messages, no prose blob, no per-turn wipe); injections as recorded additions (recorded once); steers and child
results as events projected in their own role at the step boundary (not glued onto observations); compaction
summarizes what clio-core holds (fix the suspected mid-turn loss with a failing-first test); UI projection shows
injections/edits/fixes; the platform-capability fallback to DSPy `History` (loud) and typed failure otherwise.

### Phase 4 — fixes + hooks as recorded, configurable events (branch `feat/recorded-fixes`)
Each deterministic fix behind a config switch (`conf.resolve`, documented in ENVIRONMENT.md), each firing
recorded + UI-visible + told to the model; hook effects (AfterModel/PostToolUse rewrites, request patches)
recorded; defaults decided by the owner.

### Phase 5 — Codex direct (after the owner logs in) + thinking pass-back + native tools
Stateful Responses chain per scope (`previous_response_id`; fix `codex/transport_ws.py:119-145` to use clio's
record of what was sent); consume Codex-direct reasoning deltas (today unconsumed); store thinking payloads
byte-exact and send back per provider; native tool calls on direct transports.

### Phase 6 — `dspy extract` (config) + relay onto MCP tasks
Literal DSPy extract behind config; completion-contract amendment doc. Relay as a declared MCP server with task
handles (per `docs/design/mcp-client-unification-2026-08.md` campaign 2).

## Critical files
- Transport: `providers/codex/sdk_client.py`, `providers/codex/sdk_transport.py`, `providers/stateful_common.py`,
  `providers/claude_code_stateful.py`, `providers/_cli_provider.py`
- Loop: `gact/agents/reactv2.py`, `gact/agents/reactv2_events.py`, `gact/agents/reactv2_upstream.py`,
  `gact/agents/builders.py`, `lm/adapters.py`, `lm/io_logging.py`
- Context: `arc/working_set_fold.py`, `arc/segments.py`, `arc/memory.py`, `gact/part_atoms.py`,
  `gact/transcript_projection.py`, `gact/session_store.py`, `gact/enrichment.py`, `gact/loop_inbox.py`,
  `gact/compaction.py`, `gact/conversation_projection.py`
- Tools: `tools/mcp_executor.py`, `tools/execution.py`, `gact/tool_observer.py`, `gact/permission_gate.py`
- Usage/measurement: `runtime/turn_lm_ledger.py`, `gact/usage.py`

## Verification
- Per phase: failing-first tests; full clio-agent suite green in the worktree venv (no failures, no skips);
  ruff + mypy; ratchet/guard scripts green.
- Live (isolated instance `opal-work/live/serve.sh` with `CLIO_USER_DIR`, Codex SDK `gpt-6-sol`, realistic
  prompts via `drive.py`): `"<exp67 path> what is this data?"`, `"does the nickel hurt growth?"`,
  `"show me the growth curves"`. Baseline 39/7/5 min, 79 steps, 9.87M input tokens. Record per turn: wall time,
  steps, input/cached/output tokens, LM vs tool time, full vs delta sends, one thread per scope; answer quality
  unchanged (DBL_MAX sentinel, ghost band columns, unflagged empty rows, RGB2 scale, clipping caught).
- Phase 2 adds the differential test vs stock ReActV2; Phase 3 adds a projection byte-stability test
  (render(n) prefix of render(n+1)) and a UI-vs-agent-projection test; Phase 4 a fix-recorded-and-told test.

---

## Appendix — verified system facts (code-read, 2026-09-28, develop c7a87d73)
- Highway: `_events` semantic log (ARC records first, highway derived); `_events/w/<span>` working-set atoms
  (fold, `ws_op` deletes, as-of-T); `_events/m` part atoms = transcript; `_events/s` state_merge.
- Turn question = files + resources + refs + memory hits + task notifications + plan reminder + todos + replan +
  prior-turn prose blob ("Earlier turns … (region/coordinates, ranked stations, staged file paths)").
- Module rebuilt every turn (tools, signature, system prompt, LM, adapter); per-message reasoning effort.
- Mid-turn steers/child results drained at tool boundaries and appended to the observation text.
- Tool call path modifies what the model sees (arg repair notes, path grounding, circuit breaker, PostToolUse).
- Thinking: in `_events` + transcript thinking parts, not in the working set; prior-turn thinking enters as prose;
  Codex-direct keeps encrypted reasoning in memory; Codex-direct reasoning deltas unconsumed; Claude signatures
  not captured. SPEC already defines `redacted_thinking {data, signature}`.
- Children: real sessions; first message = task text + seed + `[workflow_state]` JSON; no parent context.
- Hooks: BeforeModel/AfterModel/PreToolUse/PostToolUse/Stop can change what the model sees; `hook.invoked` audited.
- Plan mode designed as a periodic appended reminder (prefix-friendly); implemented as question concat.
- Stale docs: `docs/tui/08-semantics-and-lifecycle.md`, `docs/providers/claude_code.md` (says fresh session per call).
