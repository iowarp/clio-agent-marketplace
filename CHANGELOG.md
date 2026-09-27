# Changelog

## [Unreleased]

### Added

- Base Agent (0.2.4) can fetch web pages and files with `web_fetch` (the
  clio-kit web MCP server, declared the same way Deep Researcher declares it)
  and can pause to ask the user a question with the native `ask_user` tool.
  Both work on runtimes that already run this pack, so it keeps no
  clio-agent floor.
- APPL-CORE Analyst (`appl-core`, 0.1.0), an analyst for any APPL-CORE
  plant-phenotyping export (an L2 agent: one export format, any experiment,
  no pack changes). On first contact it reads the export's self-description,
  runs bundled audit scripts (`inventory.py`, `audit_columns.py`,
  `join_keys.py`, `flag_check.py`), and records an experiment card, a saved
  loader, and validated views under the export's `.clio/` directory
  (`card.py` keys the card by the manifest's SHA-256 and verifies loader and
  view hashes). Onboarding can run in a child agent (`audit-dataset`); the
  parent re-runs the returned loader before trusting the card. Skills carry a
  level keyword (`level:L0`/`L1`/`L2`); the L1 phenotyping skills are drafts
  with JSON Schemas and a validator for the design, observations, spectra,
  assets, and events views; the L2 skills are placeholders until the
  falsifier experiment decides their content. `geometry-to-glb` converts
  vertices/faces/colours text, PLY, and point clouds into viewport meshes.
  The pack ships `.lint-l3` and `lint-denylist.txt` for the skill-literal
  linter, black-box eval cases with a grader and a held-out variant maker,
  and requires clio-agent 0.9.4.19 or newer (for `clio.mesh-viewport.v1`).
  CI runs its tests in a new `appl-core-pack` job.

- Factorio Flat (0.3.0) can show Abaqus geometry and results interactively.
  The new `abaqus-visualization` skill ships the exporter (`odb_to_glb.py` for
  ODBs, `fea_glb.py` for `.inp` meshes and Tosca STLs) that writes `.glb`
  meshes with node and cell fields over frames, and `render_view.py`, which
  draws report figures from the same files and the camera the scientist
  chose. The new `visualize-topology-optimization` skill and `abaqus-topology`
  pack catalog show a topology run two ways: before and after in two linked
  3D viewports with a von Mises stress toggle on one shared scale, and the
  design history with a density threshold slider, a design-cycle slider, and
  the convergence plot. `TopologyViewport` aliases the `clio.mesh-viewport.v1`
  kernel and `ParameterSlider` the `clio.slider.v1` kernel, a slider with a
  step and a box to type an exact value (both clio-schemas 0.4.0). Factorio Flat
  now requires clio-agent 0.9.4.19 or newer for its pack catalog (raised from
  0.9.4.17: that release reads the `a2ui_catalogs` list form but does not pin
  clio-schemas>=0.4.0, so TopologyViewport/ParameterSlider cannot load).

## [0.6.5] - 2026-09-24

### Changed

- A2UI catalogs are now declared per agent. clio-agent 0.9.4.17 makes an
  agent's `a2ui_catalogs` the complete list of catalogs it may produce
  against, in preference order, with nothing implicit. Every shipped agent
  lists the builtin `clio-workspace` catalog, so every one keeps A2UI: Base
  Agent (0.2.3), Factorio Flat (0.2.1), SPOTTER AI (0.3.1), Cluster Operator
  (0.1.1), Data Semantics (0.1.1), Deep Researcher
  (0.1.1), Document Production (0.1.1), EarthScope Flat
  (0.1.1), EarthScope (0.1.1), Factorio
  (0.1.1), Phenotype (0.1.1), and NIFC (0.1.1).
  EarthScope Skills (0.3.1) lists `clio-workspace` first, as the default for
  tables, charts, and metrics, then its own `earthscope-stations` catalog.
  A station view names its catalog; clio-agent's generated catalog skill
  states the catalogId. No shipped pack lists the builtin Basic catalog.
- EarthScope Skills uses the list form of `a2ui_catalogs`
  (`- earthscope-stations: catalogs/earthscope-stations`). Its README
  describes the per-agent rule for pack authors.
- EarthScope Skills now requires clio-agent 0.9.4.17 or newer, the first
  release that reads the list form; an older runtime would drop its station
  catalog. The other packs list only builtins, which an older runtime still
  offers, so their floors are unchanged.

## [0.6.4] - 2026-09-23

### Added

- Base Agent (0.2.2) declares `view_image` and `view_pdf`, so the PDF workflow
  CLIO gives it can inspect rendered pages of drawings and scans, and read a
  PDF natively on a PDF-capable model.
- Factorio Flat declares `view_pdf`, and the `work-with-pdfs` skill reads a PDF
  natively with it when the connected model is PDF-capable, falling back to
  the conversion and rendered-page workflow otherwise (requires clio-agent
  0.9.4.15 or newer).
- EarthScope Skills ships its own A2UI catalog (`earthscope-stations`,
  `catalogs/earthscope-stations/`): a `StationMap` (aliasing `clio.map.v1`)
  and a multi-select `StationPicker` (aliasing `ChoicePicker`), alongside the
  Basic `Text`/`Column`/`Row`/`Button` components, delivering a structured
  `earthscope.stations.selected` domain event — no clio-agent or gact-tui
  source change required. See `earthscope-single-agent/README.md`'s "Custom
  A2UI catalogs" section for how a pack author adds one.
- Factorio Flat can prepare existing PDFs as bounded Docling text, structured
  JSON, and rendered page images, including a visual-only path for engineering
  drawings, scans, equations, and other layout-dependent evidence.
- Factorio Flat includes a separate PDF-report creation skill which activates
  only when a scientist explicitly requests a PDF deliverable; ordinary reports
  remain Markdown.

### Changed

- EarthScope Skills' acquisition procedure and root prompt route station
  selection through the new catalog skill (`a2ui-catalog-earthscope-stations`)
  and the `earthscope.stations.selected` event instead of the generic
  `ChoicePicker` + `agent.submit` recipe.

### Fixed

- PDF guidance now uses materialized workspace paths for both `@` references
  and uploaded sources, distinguishes rendered output from actual visual
  inspection, and prohibits guessing dimensions or units from extracted labels.
- SPOTTER AI syncs its environment when its MCP server starts instead of
  running against a possibly stale one.
- EarthScope Skills now requires clio-agent 0.9.4.15 or newer (the first
  release that serves its A2UI catalog) instead of an unreleased 0.9.5.

## [0.6.3] - 2026-09-13

### Added

- Base Agent, a configurable general-purpose blueprint with native workspace
  tools and no hidden routing hierarchy.
- EarthScope Skills, a focused single-agent GNSS workflow with optional regional
  fanout, interactive station selection, analysis, visualization, and reporting.
- Factorio Flat, a small-model-friendly scientific research blueprint with
  bounded evidence fanout, review, virtual-lab, and Abaqus handoff skills.
- Daisy Quach's Factorio Flat materials-science expansion, adding specialists
  for materials, manufacturing, characterization, mechanical testing,
  fatigue and failure, and scientific data analysis alongside the original
  research and simulation experts.
- A standalone phenotype workload package and provider-aware SPOTTER AI
  provenance services for native, Flowcept, CMF, and JSONL stores.

### Changed

- Deep Researcher uses committed child waits, explicit artifact source records,
  and standardized citations.
- EarthScope blueprints inherit the session model, preserve user station choice,
  use reviewed installed MCP launchers, and prefer interactive scientific views.
- Cluster Operator uses the relay's held-channel artifact list and read tools and
  aligns its expert signature with the runtime's populated question field.
- Marketplace policy now validates model pins, parsed blueprint contracts,
  native orchestration prompts, and behavioral Factorio outcomes.

### Fixed

- EarthScope single-agent acquisition stages a selected station directly from
  verified catalog evidence rather than reapplying an earlier discovery radius.
- Factorio Flat rejects contradictory traces, empty completed-child results, and
  ungrounded completion claims.
- SPOTTER retains anomaly acknowledgements and removes environment-pinned model
  selection so the active session provider remains authoritative.
