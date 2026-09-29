# HANDOFF: APPL-CORE clio agent (OPAL demo)

Written 2026-09-27 for whoever continues this work (e.g. Codex). Goal: finish, verify, and take
everything to **merge + release**. **Nothing is merged or pushed yet.**

## 0. Read first
| File | Why |
|---|---|
| `D:\Libraries\Documents\Obsidian\60-Projects\spotter\OPAL Clio Agent Plan.md` | Decided principles (levels L0–L3, no format MCP, lessons as checks, generic UI). Don't re-argue these |
| `C:\Users\jaime\.claude\plans\curious-questing-kazoo.md` | Approved dev plan: workstreams A–E, milestones |
| `D:\Libraries\Documents\Obsidian\60-Projects\spotter\OPAL Dataset Report.md` | The data. §9 = the known trap list (the eval answer key) |
| `D:\Libraries\Documents\Obsidian\60-Projects\spotter\OPAL Agents Repo Review.md` | ORNL's agent. Only the bundle-loader ideas and the trap list are worth reusing |
| `opal-work\clio-agent-pack-skill\.claude\skills\author-agent-pack\` | The pack-authoring skill that came out of this work (levels, anatomy, data agents, UI, checklist) |

## 1. Owner's rules (non-negotiable)
- **Feature branches only**, off `develop` (or `main` where there's no develop), in `git worktree`s under `D:\Libraries\Documents\projects\opal-work\`. **Don't merge, push or open PRs until the owner says so.** Ask before pushing.
- **Commits:** conventional messages, **no AI attribution** (no `Co-Authored-By`).
- **Python:** `uv`, `ruff check --fix && ruff format`, type hints, pytest. Failing or skipped tests count as failures.
- **Live tests:** use **Codex through the SDK** (not Codex direct), with **realistic human prompts**: short and vague ("<path> what is this data?"), never scripted tool steps.
- **No hardcoded experiment facts in packs.** The skill-literal lint enforces this.
- **Packs don't set the agent's limits.** No "read-only data" rules, no scripts that refuse locations, no trimmed tool lists. Give the agent base-agent's general toolset and state defaults; clio's approval modes, deny rules, allowed roots and sandbox (and the user) decide. See `author-agent-pack` → Non-negotiables.
- **Never point a test instance at the owner's real clio state.** Always set `CLIO_USER_DIR` (see §5). An earlier run without it rewrote 3 global packs in `%LOCALAPPDATA%\clio-agent\agent-blueprints`. The owner said that's fine, but don't repeat it.

## 2. Branches (all rebased on the v0.9.4.20 / gact-tui v0.11.2.21 release)
| Repo | Worktree (`opal-work\…`) | Branch | Base | Commits |
|---|---|---|---|---|
| clio-schemas | `clio-schemas-chart` | `feat/chart-kernel` | main (0.4.1) | `b51cad2` add `clio.chart.v1` + selection bindings (**0.5.0**); `d2262e7` dataQuery matches the server, `selectData` gets path/field |
| clio-agent | `clio-agent-table-query` | `feat/artifact-table-query` | develop | `4d5c59d4` POST `/v1/artifacts/{id}/table-query`; `dc3a76c1` tests; `be92df27` lazy numpy/pyarrow |
| clio-agent | `clio-agent-chart-guidance` | `docs/chart-presentation-skill` | **stacked on** table-query | `a8f5144b` presentation skill → chart presets + linked selection; `acc409bc` **branch-local** clio-schemas 0.5.0 path pin; `6b6e20db` Altair section + `scripts/vega_spec.py` |
| clio-agent | `clio-agent-pack-skill` | `docs/author-agent-pack-skill` | develop | `f6018ece` `.claude/skills/author-agent-pack/`; `4320a024` lesson: packs don't set limits |
| gact-tui | `gact-tui-chart` | `feat/chart-kernel` | develop (mesh viewport already merged upstream) | `7beabf20` chart renderer (Vega-Lite, lazy) + linked selection (table, map); `b1c439d1` dataQuery / `selectData` |
| marketplace | `marketplace-lint` | `feat/skill-literal-lint` | main | `56d5499` `scripts/check_skill_literals.py` + tests + CI + CONTRIBUTING |
| marketplace | `marketplace-appl-core` | `feat/appl-core-pack` | main | `5edb016` pack + L0/L1 skills + scripts; `3a389d7` evals/grader/variants; `e87dc28` variant empty-table fix; `a74dcc0` dataset artefacts in the workspace store; `9e97a7b` how the agent writes (create_artifact); `34cca15` pack-imposed limits removed, base-agent toolset (+ clio-kit `web` server for `web_fetch`) |

**Test status after the rebase: not re-run on most branches** (the owner said not to test during the rebase). Before the rebase, all passed. Re-run everything (§4).

## 3. What each piece is
- **clio.chart.v1** (clio-schemas + gact-tui):
  - a generic Vega-Lite chart;
  - a spec guard (Python `chart_spec.py` + TS port, shared fixtures in `tests/fixtures/chart/`);
  - core presets `trajectories|heatmap|spectra|boxplot|scatter`;
  - `selection` bound to `/selection/<key>` = `{field, values[], source?}`, so linked views (chart ↔ data-table ↔ map) work client-side with no agent turn.
- **table-query** (clio-agent): pyarrow filter/aggregate/stride/per-entity LTTB over CSV/Parquet artifacts. Config keys are `artifacts.table_query_*`.
- **Presentation skill** (`builtin_skills/present-interactive-analysis`): chooses views, favours presets, covers Altair authoring on `alt.NamedData("source")`, and bundles `scripts/vega_spec.py build|check`. The owner wanted this in the existing skill, not a new builtin.
- **appl-core pack** (marketplace): APPL-CORE Analyst, an honest L2 agent.
  - **Skills:**
    - L0: `onboard-dataset` (+ `inventory.py`, `audit_columns.py`, `join_keys.py`, `flag_check.py`, `card.py`), `audit-dataset` (spawned child), `evidence-and-claims`, `geometry-to-glb`.
    - L1 drafts: phenotyping onboarding, growth, treatment-response, physiology, report, + 5 view schemas + `validate_views.py`.
    - L2: `appl-core-exports` and `appl-instruments` are **placeholders**.
  - **Also:** `.lint-l3` + `lint-denylist.txt`; evals (17 cases, grader, `make_variants.py`).
- **Drafted L2 skill content:** `opal-work\handoff\appl-skills-draft\{appl-core-exports,appl-instruments}\SKILL.md`. Copy into the pack's `skills/` when ready, and keep the **[candidate]** markers until a second export confirms each check.

## 4. Remaining work → merge → release

### 4a. Re-verify every branch (use each worktree's own `.venv`: `.venv\Scripts\python.exe -m pytest`, NOT `uv run pytest`, which picked up the main repo's pytest from PATH)
- **clio-schemas-chart:** full pytest, ruff, pyright, `export --verify`, ts-gen check.
- **clio-agent (both branches):** `pytest tests -n 8` (at least the a2ui/catalog/skill/artifact subsets), ruff, `mypy src/`. Known pre-existing failure: `test_collabora_wopi_locks_guard_editor_saves` (fails on develop too).
- **gact-tui-chart:** `pnpm install && pnpm lint && pnpm typecheck && pnpm test && pnpm build`.
- **Marketplace (both):** `uv run --no-project python -m unittest discover -s tests`, `scripts/check_model_pins.py .`, `scripts/check_skill_literals.py .` (lint branch), and the pack tests (see the `appl-core-pack` job in `.github/workflows/ci.yml`).

### 4b. Live tests (Codex SDK) and finishing the L2 skills
- **Before re-running:** reinstall the pack (`drive.py` does it on every run) so sessions get the workspace-store + no-limits fixes. Runs in `runs\*` from before those fixes are invalid.
- **Status at handoff:** two sessions were running (transcripts land in `opal-work\live\runs\<name>\`):
  - `exp67-first-contact`: *"<67 path> what is this data?"*, *"does the nickel hurt growth?"*, *"show me the growth curves"*;
  - `variant-categorical`: *"<variant path> what's in here?"*, *"does the treatment matter for growth?"*.
- **Still to run:**
  1. A **second session on 67**: *"<path> which genotypes did best?"*. Expect it to reuse `<workspace>\.clio\datasets\<manifest-sha16>\experiment-card.md` and not re-profile.
  2. The **unbalanced variant**: `opal-work\variants\exp-unbalanced`.
- **Score each run** against Dataset Report §9 (evals grader: `appl-core\evals\scripts\evaluate_appl_core.py`).
- **Then update the L2 skills:** traps the generic skills missed on **both** exports go into `appl-core-exports` / `appl-instruments` as checks (start from the drafts in §3).
- **Also check in the live UI** that a chart surface renders: needs gact-tui `feat/chart-kernel` built and served against this instance.


### 4b-result. First valid live run (exp 67, fixed pack, Codex SDK gpt-6-sol), `liveuns\exp67-first-contact\`
- Turn times: 39 min ("what is this data?", full onboarding via the audit child: 79 serial steps, 9.87M input tokens), 7 min (nickel), 5 min (growth curves).
- **Traps caught (vs Dataset Report §9):** FC1 max-float sentinel (exactly 328,740), VNIR/SWIR ghost string band columns (473/634), near-universal `low_mask_coverage`, canopy clipping (excluded ROI-edge-contact images), FC1 duplicate provenance, inconsistent `sample_key` formats, empty data-issues vs dirty data, zero weights, treatment kept categorical + asked for unit. **Also found things the manual report missed:** extreme roundness when perimeter = 0, 12 duplicate weight readings, `-99`/`9999`/`32767` sentinel candidates.
- **Missed / unclear:** MSC1 invalid-source blanks, the RGB2 mm-scale problem (it sidestepped by using `area_px`), the 1004 g weight spike, the species misspelling.
- **Answers:** paired within-genotype comparison, explicitly not causal, unit asked for; growth curves were a matplotlib PNG + CSV, not the interactive `clio.chart.v1` (check why the chart component wasn't used).
- **Main problem is speed:** serial tool execution + every step a cold, full-history model call. See the provider investigation / issues.

### 4c. Merge + release order (only when the owner says go)
1. **clio-schemas `feat/chart-kernel`** → PR to main → release **0.5.0** (tag + publish per that repo's process).
2. **clio-agent:**
   1. PR `feat/artifact-table-query` → develop.
   2. On `docs/chart-presentation-skill`, **replace the branch-local pin**: drop the `[tool.uv.sources] clio-schemas = { path = "../clio-schemas-chart" }` table, keep `"clio-schemas==0.5.0"`, and run `uv lock`.
   3. PR it → develop.
   4. PR `docs/author-agent-pack-skill` → develop.
3. **gact-tui `feat/chart-kernel`** → develop. Its fixtures must byte-match the released clio-schemas 0.5.0 catalog; re-sync the fixtures and manifest hashes if 0.5.0 changed.
4. **Marketplace:** `feat/skill-literal-lint` → main, then `feat/appl-core-pack` → main. Bump `appl-core`'s `requires.clio_agent` floor to the clio-agent release that carries clio-schemas 0.5.0 and the table-query route.
5. **Release clio-agent** with the in-repo skill `.claude/skills/release-clio/SKILL.md` (merge develop→main, bump version, pin submodules for gact-tui + marketplace, tag, verify CI). The gact-tui and marketplace submodule pointers must reference the merged commits.

## 5. Running an isolated live instance (Windows)
Launcher: `opal-work\live\serve.sh`. Driver: `opal-work\live\drive.py NAME "prompt" ["prompt" …]`. Key env:
```
CLIO_USER_DIR=opal-work\live\user          # isolates config/data/cache/global blueprints
CLIO_CODEX_VARIANT=sdk
CLIO_DATA_DIR=opal-work\live\state\.clio_agent
CLIO_ALLOWED_ROOTS=<ws>;<OPAL export>;<opal-work\variants>
CLIO_SHELL_MAX_COMMAND_CHARS=20000  CLIO_SHELL_DEFAULT_OUTPUT_BYTES=65536  CLIO_SHELL_MAX_OUTPUT_BYTES=524288
```
- **Run it:** `.venv\Scripts\python.exe -m uvicorn clio_agent.gact.app:app --port 17990` from `clio-agent-chart-guidance`.
- **Bind the model:** `PUT /v1/providers/lm` with `{"provider":"codex","variant":"sdk","api_base":"codex://sdk","model":"gpt-6-sol","api_key":"x"}`. The field is **`variant`**, not `codex_variant`.
- **Create sessions with `"approval_mode": "bypass"`** (`drive.py` does). Without it, `shell_bash` is denied by the permission gate, and the agent can only report what the manifest and README say. That's what happened in the runs kept as `runs\*-GATED`: the agent behaved honestly (labelled everything unverified and refused to estimate effects), but the test was invalid. A turn with `gpt-6-sol` takes about 10–12 min.
- **Live finding (fixed on `feat/appl-core-pack` after this was written):** the pack originally wrote the card, loader and views to `<bundle_root>/.clio/`, but clio's system prompt tells agents to write artifacts in the workspace. The agent resolved the conflict by deciding the data was read-only, and didn't onboard. The new contract is `<workspace>/.clio/datasets/<manifest-sha16>/`, with `card.py ... --store <workspace>`. After this fix, re-run the live sessions.
- **Segfault seen:** the server crashed once (exit 139, no Python traceback; log kept as `live\server-segfault-*.log`) with 3 turns active at the same time, including a turn whose driver had been stopped (server-side turns keep running after the client is killed). Run sessions one at a time, restart and rebind after a crash, and report it upstream if it recurs.
- **Bug found live (fix pending):** the dataset key is the manifest SHA-256 alone, so two different datasets with byte-identical manifests collide. The `categorical_treatment` variant only changes design tables, so it collides with the original 67 (`76bf90275f7a9839`), and a card from one gets reused for the other. Fix in `card.py`: key on the manifest plus a fingerprint of the table files (size + sha256, or Parquet footer metadata), and make `status` report `stale` when the fingerprint differs. Then re-run the variant with a clean store.
- **Stop it:** kill by port (`Get-NetTCPConnection -LocalPort 17990`); stopping the bash wrapper leaves python running.
- **Data:** the OPAL export is at `D:\Libraries\Documents\projects\OPAL\67_…\67_…`. Variants are in `opal-work\variants\`, made with `make_variants.py`, which copies tables/docs only and never writes to the source.

## 6. Open issues / follow-ups
- **iowarp/clio-agent#1487:** shell drops output past the cap (proposal: spill to a file). For now, raise the limits with env vars.
- **`earthscope-single-agent/skills/compare-earthscope-coverage/SKILL.md`** calls `load_skill(..., task=…)`, which doesn't exist (should be `spawn_skill_task`). Its test asserts the wrong text.
- **Strict lint on existing packs would flag:** earthscope-gnss-region 14, earthscope-flat 5, data-semantics 22 (mostly speedup claims), cluster-operator 1. Adding `lint-denylist.txt` for the station IDs would be needed before opting those packs in.
- **Vega-Lite read-back** writes an internal store (`<param>_store`), pinned to vega-lite 6.4.3 and guarded by a test.
- **`selectData`** now requires `path`/`field`; that's a breaking change for any producer sending only `{rowIds}`.
- **Cross-surface linked selection** isn't built; same-surface only.
- **Point clouds:** the mesh viewport has no glTF POINTS support; `to_glb.py` refuses point clouds.
- **Questions for the APPL owners:** listed in the Dataset Report §11 and the `appl-instruments` draft (treatment = nickel mg/kg per ORNL's KB, RGB2 mm scale, FC1 protocol steps, MSC1 blanks, weight tare, timezone).
