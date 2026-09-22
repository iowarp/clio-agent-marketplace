# Changelog

## [0.6.4] - 2026-09-22

### Added

- Factorio Flat can prepare existing PDFs as bounded Docling text, structured
  JSON, and rendered page images, including a visual-only path for engineering
  drawings, scans, equations, and other layout-dependent evidence.
- Factorio Flat includes a separate PDF-report creation skill which activates
  only when a scientist explicitly requests a PDF deliverable; ordinary reports
  remain Markdown.

### Fixed

- PDF guidance now uses materialized workspace paths for both `@` references
  and uploaded sources, distinguishes rendered output from actual visual
  inspection, and prohibits guessing dimensions or units from extracted labels.

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
