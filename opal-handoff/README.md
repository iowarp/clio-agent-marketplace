# OPAL / clio work — handoff snapshot (WIP branch, not for merge)

Non-git working material preserved before a machine clean (2026-09-28).

- `HANDOFF.md` — OPAL integration handoff: branches, merge/release order, findings.
- `appl-skills-draft/` — draft L2 skills (appl-core-exports, appl-instruments).
- `live/` — isolated live-test harness (`serve.sh`, `drive.py`) + run transcripts/logs
  (`runs/exp67-first-contact` is the 39-min Codex-SDK baseline).
- `dspy34-spike/` — DSPy 3.4.0 spike scripts (findings in the Obsidian doc
  "LM Transport Statefulness and DSPy", section 8).
- `clio-loop-rebuild-plan.md` — approved plan: approach B (ClioReAct on DSPy 3.4,
  clio-core as the context system); Phase 1 = clio-agent `feat/codex-sdk-stateful`.

Pushed work branches: clio-agent `feat/codex-sdk-stateful`, `docs/chart-presentation-skill`,
`docs/author-agent-pack-skill`, `feat/artifact-table-query`; clio-schemas `feat/chart-kernel`;
gact-tui `feat/chart-kernel`; clio-agent-marketplace `feat/appl-core-pack`, `feat/skill-literal-lint`.
