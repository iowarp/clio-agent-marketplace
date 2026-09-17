# Changelog

## [Unreleased]

### Added

- EarthScope Skills ships its own A2UI catalog (`earthscope-stations`,
  `catalogs/earthscope-stations/`): a `StationMap` (aliasing `clio.map.v1`)
  and a multi-select `StationPicker` (aliasing `ChoicePicker`), alongside the
  Basic `Text`/`Column`/`Row`/`Button` components, delivering a structured
  `earthscope.stations.selected` domain event — no clio-agent or gact-tui
  source change required. See `earthscope-single-agent/README.md`'s "Custom
  A2UI catalogs" section for how a pack author adds one.

### Changed

- EarthScope Skills' acquisition procedure and root prompt route station
  selection through the new catalog skill (`a2ui-catalog-earthscope-stations`)
  and the `earthscope.stations.selected` event instead of the generic
  `ChoicePicker` + `agent.submit` recipe.

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
