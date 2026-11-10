# Changelog

## [Unreleased]

### Added

- `ndp` agent (1.0.0): the standard agent plus the `ndp` plugin, for National Data
  Platform work.
- `geodesy` (1.1.0): `station_catalog.py within` lists a normalized catalog's stations
  within a great-circle radius (nearest first, with input rows and invalid skips), so
  the region and coverage skills work when the geo MCP server is not running.
- `wtfp` (0.9.0), pinned from `JaimeCernuda/wtf-p` (`clio-plugin/` at `e23d3cf8`): WTF-P's
  method for writing a scientific paper from evidence, as a CLIO plugin. Its project
  records, 36 actions as `/wtfp:*` commands, 7 skills, 11 roles as subagents and write
  guard; the paper's LaTeX is built by `latex`, which it requires. The index lists it in
  `plugins[]` with its git source and commit. No agent includes it by default; add it to
  a conversation's agent.
- `marimo` (1.0.0): pair with the person on a live marimo notebook. It vendors
  marimo-team's own `marimo-pair` skill unchanged (Apache-2.0, pinned commit in its
  `NOTICE`) and adds `use-marimo`: start the notebook server in the background, open it
  in the shared browser (which starts its kernel session), then read and change the
  running notebook through marimo-pair.
  No agent includes it by default; add it to the agents that should pair on notebooks.
- `browser` (1.0.0): the in-app browser the agent drives from `run_code`. It claims
  CLIO's ten browser tools as script-only (`browser_evaluate` asks by default), ships
  the `browser` kernel binding (`ai.iowarp.clio/kernel/browser.py`, Playwright's names
  over those tools), the `browser.use` fragment and the `use-the-browser` skill, and
  joins the standard agent. The skill says what `browser_certificate_untrusted` and
  `browser_host_unreachable` mean (only the person trusts a certificate; an unreachable
  host is unreachable from the agent's computer), and the facade notes when the browser
  restarted under a page to trust a certificate.

### Changed

- `ndp` (2.0.0) is now the NDP package. It claims CLIO's built-in NDP tools
  (organization lookup and dataset search directly; Endpoint connect, operations,
  request and upload deferred) and owns the `work-with-ndp` skill, retitled "Working
  with NDP" and moved from `connected-data`. The skill no longer says the tools
  activate after an attached dataset or saved Endpoint, explains what an NDP
  organization is, and needs no MCP server; the clio-kit `ndp` server is declared
  `callers: "code"`, an optional `run_code` extra (`tools.ndp.*`).
- `connected-data` (2.0.0) keeps generic sources and knowledge stores; its NDP tool
  claims moved to `ndp`. `connect-data` says to load `work-with-ndp` when the agent has
  the `ndp` plugin and otherwise not to claim an NDP search it cannot run. The
  standard agent therefore no longer carries NDP search; use the `ndp` agent or add
  the `ndp` plugin.
- `earthscope` (0.6.0) adds only EarthScope's organization conventions on top of
  `ndp`: `acquire-earthscope-gnss` uses the built-in NDP tools instead of the `ndp_*`
  MCP tools and says which records are EarthScope's per-station position series,
  station catalog (which can lack an organization) and services. The `earthscope`
  agent (0.7.0) builds on the `ndp` agent.
- `geodesy` skills use `geo_geocode` / `geo_filter_points_by_radius` when available and
  otherwise a cited lookup and `station_catalog.py within`.
- `latex` (1.2.3): `start-a-paper` keeps only the template's mechanics (`main.tex`
  `\input`s the files under `sections/`); how to divide a paper into sections is the
  writing method's choice, which `wtfp` makes.
- `latex` (1.2.2): `author-latex-pdf`, `start-a-paper` and the `latex.build` fragment say to register a figure a script draws with
  `create_artifact` and its script and data in `used`, so a comment on the figure in the PDF
  names the script. Unregistered, the comment said the figure's producer was unknown.
- `latex` (1.2.1): `author-latex-pdf` covers checking whether a paper is ready for a venue
  (page limit, double-blind review, required packages, paper size), and the `latex.build`
  fragment says page counts and venue checks are measured on the built PDF, not read from
  the source. Asked whether a paper was ready for a venue, the agent had answered from the
  source without building.
- `latex` (1.2.0): a build makes the paper, one artifact shown by its title and built from
  the versions of the source files it read. Each `template.yaml` names the paper's
  `document_type` and its `venue`, which the paper's card shows ("Paper", "IEEE
  conference"). `author-latex-pdf`, `start-a-paper` and the `latex.build` fragment say
  that the paper is the deliverable, set `\title` early, and leave the PDF's path out.
- `latex` (1.1.0): builds go through CLIO's `latex_build` tool, which CLIO implements
  with the pinned Tectonic 0.17.0. The tool reports every problem by file and line, and
  with a venue it also checks the paper against that template's rules.
  `author-latex-pdf` is rewritten around the tool, and its `scripts/render_latex.py`, a
  second Tectonic call, is deleted. The plugin now ships `templates/`:
  `ieee-conference`, `ieee-journal`, `acm-sigconf` (review, anonymous), `acm-journal`,
  `springer-lncs` and `elsevier`. Each has a `template.yaml` with its class, options
  and venue rules (page limit, references, double-blind, packages, paper size), and a
  starting project that builds with its citation resolved. The new `start-a-paper`
  skill says how to begin from a template, and the `latex.build` fragment says the
  templates and venue checks exist. `latex_outline` (sections, figures, tables and
  equations with their source lines and PDF pages) and `latex_locate` (a PDF point to
  its source line and back) are declared too.
- `document-production` (0.2.2): the anchor reference reads the Source, Figure and
  Graphics lines of a mark on a LaTeX paper's PDF.
- `document-production` (0.2.1): `review-document-artifact` and its anchor reference
  read the comment entries CLIO now sends: a header naming the version and what to
  edit, a labelled overview and crops, and one entry per mark (S1, S2, ...) with its
  Selected, Under, Source, Picture and Made by lines. The answer is stored as the reply
  on each comment, so it goes by label.
- `visuals` (1.2.2): `review-visual-presentation` says how to act on a figure comment:
  change the producing script, rerun it, look at the new image with `view_image`.
- `pptx` and `xlsx` (1.0.1): their editing skills find a comment's slide shape or cells
  from the entry's Source line, since comments no longer carry raw anchor profiles.

## [0.7.0] - 2026-10-28

The marketplace is rebuilt around `ARCHITECTURE.md`: each kept agent ships its
own plugin whose `mission` fragment says whom it serves and what it does; L1
method plugins hold no program; programs, formats and sources are separate L2
plugins; every plugin with domain content carries the skill-literal lint.

### Added

- `clio-data` (CLIO Data): inspects, checks and converts HDF5/netCDF-4, ADIOS2
  BP4/BP5 and Parquet files, with a verified conversion script
  (`convert_to_parquet.py`: written, read back, rows, nulls, NaNs and
  per-column checksums compared). It replaces `data-semantics` and
  `format-bridge`.
- Plugins `adios` (clio-kit's adios server plus an `adios2` skill),
  `data-onboarding` (L0, shared by clio-data and OPAL), `phenotyping` (L1),
  `geodesy` (L1, with `fit_trajectory.py` and `station_catalog.py`),
  `fea-methods` (L1), and the program plugins `morphorm` and `slurm`, which
  carry DaisyQuach's factorio-flat 0.5.0 work: the Morphorm workflow, its
  restart and bundled checks (`exo_summary.py`, `xml_params.py`,
  `diag_summary.py`), `hpc-batch-jobs` with `wait_job.sh`, and their tests.
- `parquet` gains its `parquet` skill; the `hdf5` skill carries the tool
  guidance; `scientific-method` gains `run-non-interactive-task`.

### Removed

- The blueprint-era demo agents `genomics-review`, `geospatial-field-review`,
  `hpc-io-regression`, `materials-crystal-review`, `ndp-environmental-hazards`,
  `proteomics-mzml-review`, `remote-sensing-ogc-review`,
  `seismic-waveform-review`, `terrain-suitability` and
  `wildfire-smoke-impact-review` (with the `wildfire` plugin and its
  smoke_review flow), with their plugins.
- `phenotype`, the synthetic workload that APPL-CORE (OPAL) replaces, with its
  plugin and the `phenotype-impl` CI job.
- `data-semantics` and `format-bridge` (folded into `clio-data`),
  `documents-review` (folded into `document-production`), `topology` (split
  into `fea-methods` and the `abaqus` and `morphorm` programs), and the
  leftover Codex `agents/openai.yaml` files.
- The smoke-test agents `hook-smoke` and `mcp-calculator-smoke` and their
  plugins leave the default marketplace, so people choosing an agent see only
  agents meant for work. They live in `testing/`, a separate marketplace named
  `clio-testing` that CLIO's own checks install; CI checks it alongside the
  default one.
- The blueprint-era topology experiments, superseded by the flat agents that
  load procedures on demand: the Factorio principal-investigator agent and the
  EarthScope GNSS region agents (`earthscope-gnss-region`, `earthscope-flat`
  and the archived depth and width topology variants), with the plugins only
  they used (`earthscope`, `earthscope-flat`, `earthscope-gnss`,
  `earthscope-gnss-region-depth`, `earthscope-gnss-region-width`).
- `base-agent` (now the `standard` agent), `cluster-operator` (retired relay
  reference with no tools left to provide) and wildfire's declared `workflow:`
  block, now the `smoke-review` flow, which runs the stages on the core
  `workflow` flow.

### Changed

- deep-researcher 0.3.0 runs deep research as the `deep-research` flow,
  shipped in its plugin (0.3.0) and started with `run_flow` (the agent adds
  `orchestration`). The flow plans directions (a recorded model step that
  chooses how many, up to `max_directions`, default 6), researches them in
  parallel (`concurrency`), has the critic verify them, researches the gaps the
  critic names for at most `max_rounds` (default 2) more rounds, and writes the
  report (a recorded model step) from verified claims only, appending the
  unresolved questions and rejected claims; the report is written to the
  workspace and its typed fields ride the result's `workflow_state`.
  `researcher_model` and `critic_model` choose each subagent's model. The
  critic returns a typed audit in `workflow_state.audit` (verified claims with
  fetched source and quote, rejected claims with reasons, gaps), which the flow
  validates. The coordinator answers simple questions directly and delivers the
  flow's report with `create_artifact`; its fragments are gated on `run_flow`
  so the subagents never read them. The `rounds`, `sources` and `verification`
  fragments and the `deep-research-report` skill are removed: the flow and the
  writer's instructions now hold that method.
- Factorio 0.6.0: its identity no longer repeats its name; `factorio.mission`
  says whom it serves, that no simulation program is the default, and that it
  runs meshes, solves and batch jobs itself when it can; a roster fragment
  makes consulting a specialist an ordinary tool call. Every Factorio subagent
  can read files, and those that compute or build can write and run them;
  each declares the plugins its skills reference.
- `manufacturing` is an L1 method pack with no program: `materials`,
  `manufacturing-processes` (was `am-process`), `characterization`,
  `mechanical-testing`, `fatigue` and `fea-methods`. `abaqus` is the Abaqus
  program plugin with Tosca, the topology views, the `abaqus-topology` catalog
  (instance values scrubbed) and `abaqus_engineer`.
- Skill merges: inconel-718 removed; pbf-lb → am-process-parameters;
  surface-finishing → post-processing; microstructure-characterization →
  microstructure; porosity-analysis → xct; fatigue-testing →
  mechanical-testing; mts-test-systems → load-frame-capability;
  scientific-plotting → data-visualization; research-methodology →
  experimental-design; formulate-abaqus-package → abaqus.
- `scientific-method` is part of the CLIO Science base, with domain-neutral
  examples; Factorio's own process skills moved into `factorio`.
- EarthScope 0.6.0: `earthscope-skills` is renamed `earthscope` (an L2 source
  plugin with a mission and discovery-based acquisition, no hardcoded resource
  literals); GNSS methods live in `geodesy`; `pandas` and `plot` are dropped.
- APPL-CORE 0.3.0 is shown as "OPAL": split into `data-onboarding`,
  `phenotyping` and `appl-core`; the export contract is version 6 and other
  versions are refused; inputs are described by convention, not as read-only;
  the `appl-instruments` placeholder is removed and `geometry-to-glb` moved to
  `visuals`.
- SPOTTER (`spotter-ai` 0.5.0) watches any CLIO session: the eight phenotype
  campaign tools are gone; alerts go through `raise_alert_card` and
  containment through CLIO's SPOTTER clearance; one mission fragment, with the
  skills investigate-provenance, inspect-attention and contain-anomaly.
- deep-researcher 0.2.0 has web only in its researcher and critic subagents and
  a mission-first coordinator prompt; document-production 0.2.0 and
  clio-search 0.2.0 lead with a mission that describes their actual tools.
- The `workspace` plugin (1.1.0) carries CLIO's read-only repository inspection
  tools `fs_list_directory` and `fs_search_text` in place of `fs_glob` and
  `fs_grep`, matching CLIO's file server.
- The `visuals` plugin's diagram guidance points at the active catalog's
  `clio.mermaid.v1` entry for families, syntax and viewer capabilities, as
  0.6.13 did for the blueprint agents; `create-diagram` covers choice and review.
- HDF5 guidance lives in the `hdf5` plugin (1.1.0) as one `hdf5` skill by the
  HDF5 team: a router plus 22 guides under `references/`, audited against HDF5
  2.0–2.2 and h5py 3.12–3.16 (from iowarp/clio-agent#1736, which proposed it
  as a CLIO built-in). Every agent that adds `hdf5` gets it. `data-semantics`
  (0.2.0) drops its 21 older `hdf5-*` skills, and its HDF5 subagent loads the
  new guides, `references/clio_core_ingest.md` for clio-core ingest.
- The marketplace moves from Agent Blueprints (`AGENT.md` plus `experts/*.md`)
  to native Agent Plugins 1.0.0 packages under `plugins/` and Python agent
  classes under `agents/`. Every agent keeps its id; experts become defined
  subagents of the plugin they belong to, root prompts become domain
  fragments, and skills move to hyphenated folders in the plugin that owns
  them. Shared capabilities (workspace, shell, web, documents, visuals,
  delegation, connected data, the clio-kit servers) are single plugins the
  agents depend on, so `create-pdf-report` and the document skills have one
  home.
- The spotter and phenotype MCP projects move to `plugins/<id>/impl` and
  launch from `${PLUGIN_ROOT}`. The archived `old/` agents are converted too;
  tools no MCP server in the repository provides are not carried. hook-smoke's
  `pre_message` is an SDK `prompt_submit` hook.
- CI runs `clio-agent plugin check .`; the policy scripts check the plugin
  layout instead of `AGENT.md`.

### Renamed

- `factorio-flat` is now `factorio` (agent and plugin, 0.5.0): the flat
  research partner replaces the earlier Factorio agent under its name.
- `earthscope-single-agent` is now `earthscope` (0.5.0): one agent loading the
  `earthscope-skills` procedures on demand. Refs to the old ids no longer
  resolve; use `clio/factorio` and `clio/earthscope`.

## [0.6.13] - 2026-10-21

### Changed

- Shared task guidance distinguishes waiting, consultation, pause and cancellation
  while retaining the assignment and returned evidence.
- Base Agent 0.2.9, APPL-CORE 0.2.6, Factorio Flat 0.4.4 and EarthScope 0.4.4
  discover diagram families through the active catalog and use read-only repository
  inspection. These pack versions require CLIO 0.9.5b8 or later.

## [0.6.12] - 2026-10-18

### Added

- CLIO Search offers bounded read-only session and file-passage search.
- Standard agents discover diagram, HTML/SVG and visual-review capabilities
  without prescribing a particular layout or requiring a diagram for every task.

### Changed

- Base Agent 0.2.8, APPL-CORE 0.2.5, Factorio Flat 0.4.3 and EarthScope 0.4.3
  share content-driven composition and captured-image review guidance.
- Shared task guidance explains accepted work, consultation and cancellation.
- APPL-CORE verifies onboarding before claiming it is ready to analyze a dataset.
- APPL-CORE presents evidence in natural prose with specific clickable references.
  Bracketed claim tags are no longer required or rewarded by the grader. Status
  commands and pending audits cannot substantiate scientific findings.
- APPL-CORE 0.2.4 investigates messy read-only source data with adaptable queries
  and code. Cards, loaders, repeat execution and the five bundled view schemas
  are optional aids. Missing or unfamiliar export versions trigger inspection
  instead of blanket refusal. Acceptance cases now require source preservation
  and grounded findings/adaptations rather than a prescribed script pipeline.
- Shared Data Semantics inspection and quality guidance preserves source data
  and distinguishes uncertain meaning from computational obstacles.

### Added

- Base Agent, APPL-CORE, Factorio Flat and EarthScope declare the shared managed
  execution/document tools. Discovery is optional for standalone paths/import
  checks; document work requests converter/font preparation separately. Pack
  versions advance and require CLIO beta 3 or later for these native tools.
- Opt-in skill literal checks reject dataset-specific facts in reusable pack prompts.
  Packs can supply a denylist, enable generic checks, and mark deliberate examples.

## [0.6.11] - 2026-10-05

### Added

- SPOTTER reads configured Flowcept attention captures with CLIO's shared profile
  reducer and attaches capture references and uncertainty to reviewed findings.
  Partial, ambiguous, mismatched and out-of-root captures produce explicit errors.

### Changed

- APPL-CORE keeps generated cards, loaders, audits and views in the owning
  workspace's Agent state, using the canonical directory supplied by CLIO.
- Marketplace qualification uses Python 3.13, matching CLIO's managed runtimes.
- APPL-CORE and SPOTTER require CLIO 0.9.5b3 for their workspace-state and
  attention handoffs; older runtimes hold the packs with an explicit version error.

The beta-3 integration has source and recorded-capture validation. Fresh Delta
inference and both OPAL demonstrations remain separate live acceptance work.

## [0.6.10] - 2026-10-02

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
  loader, validated views, and audit reports in the active workspace under
  `.clio/datasets/<key>/`, where `<key>` comes from the SHA-256 of the
  export's manifest (`card.py --store <workspace_root>`; it also verifies
  loader and view hashes). Keeping these out of the export by default leaves
  the raw data pristine, works with shared data mounts, and lets another
  session or path find the same export again; the pack sets defaults only
  and leaves what may be written to clio's approval modes, deny rules,
  allowed roots, and sandbox. The expert carries Base Agent's
  general-purpose tools (file edits, `view_image`, `view_pdf`, `web_fetch`). Onboarding can run in a child agent (`audit-dataset`); the
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

- The domain agents are now supersets of the standard agent (Base Agent):
  APPL-CORE Analyst (0.2.0), Factorio Flat (0.4.0) and EarthScope Skills
  (0.4.0) each have everything Base Agent has, plus their own domain.
  - Tools: the root expert declares all of Base Agent's tools (`shell_bash`,
    file read and edits, `view_image`, `view_pdf`, `web_fetch`, `ask_user`).
    EarthScope Skills gains all of them and the clio-kit web server;
    Factorio Flat gains file read/edit and `web_fetch`.
  - Skills: each declares clio's built-in `work-with-pdfs`, `planning`,
    `update-models` and `present-interactive-analysis`, which Base Agent gets
    automatically, and ships `create-pdf-report`. Factorio Flat drops its own
    copy of `work-with-pdfs` (identical to clio's) and uses the built-in.
  - A2UI tools come from each agent's declared catalogs, as Base Agent's do,
    instead of a partial explicit list.
  - Prompts: Base Agent's working principles are now a `## Working principles`
    section (stay grounded in inspected content, smallest tool sequence,
    report failures plainly, verify edits, and when to read or write a PDF),
    carried word for word by each domain agent.
  - Base Agent (0.2.5) ships `create-pdf-report`, so writing a PDF on request
    is part of the standard agent.
  - A new test, `tests/test_standard_agent_superset.py`, reads Base Agent as
    the source and fails if a domain agent lacks any of its tools, MCP
    servers, catalogs, skills or principles.
  - APPL-CORE Analyst requires clio-agent 0.9.4.23 or newer, the first release
    whose catalog has the `clio.chart.v1` presets its views use.

### Changed

- `clio.time-series.v1` is removed upstream in favor of one Altair/Vega-Lite
  chart layer (`clio.chart.v1`, clio-schemas 0.5.1); the two packs that used
  it move over (#1533). Factorio Flat's `abaqus-topology` catalog
  re-expresses `ConvergencePlot`'s `xKey`/`yKeys`/`series` as the
  `trajectories` preset's `xField`/`yField`/`entityField` over inline `data`
  (or `dataUri`). EarthScope Skills' `visualize-earthscope-gnss` primary plot
  moves to `clio.chart.v1` with a Vega-Lite `spec` authored through
  `present-interactive-analysis`'s Altair support, folding the confirmed
  `east`/`north`/`up` columns into one line per component (no named preset
  reshapes a wide table that way). Both packs' `requires.clio_agent` floor is
  raised to `>=0.9.4.23`, the first clio-agent release that pins
  clio-schemas>=0.5.1.

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
