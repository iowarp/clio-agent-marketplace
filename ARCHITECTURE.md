# Marketplace architecture

This marketplace ships a small set of agents built from plugins. The rules below
decide what an agent is, where a piece of knowledge lives, and what a plugin may
claim. `CONTRIBUTING.md` covers the file layout and the checks.

## What an agent is

An agent is an identity plus a plugin selection (`agents/*.py`). CLIO composes its
main prompt in this order:

1. one identity line, `You are {name}, {role}.`;
2. core guidelines and rendering;
3. capability fragments from each plugin;
4. domain fragments.

The identity line is all the class contributes. So **every agent ships its own
plugin, named after the agent, whose first fragment is `mission`**. The mission
says, in at most 150 tokens:
- whom the agent serves and what they come for;
- its scope and its honest level (see below);
- which of its specialists and programs to reach for, and when;
- how it delivers.

The rules for `role` and the mission:
- `role` never repeats the name. It reads naturally after "You are {name},".
- The mission states defaults and conventions, never prohibitions. CLIO's
  approval modes, sandbox and allowed roots decide what is permitted; a prompt
  that says "treat the data as read-only" makes an agent refuse work CLIO allows.

## Levels

Every skill and fragment lives at one level, and the plugin that holds it is
named for that level (see `.claude/skills/author-agent-pack` in clio-agent).

| Level | What it holds | Examples here |
|---|---|---|
| L0: general habits | how to onboard data, analyse, report, cite | `scientific-method`, `data-onboarding`, `visuals`, `workspace` |
| L1: domain methods | how a field reasons, independent of any program or dataset | the `manufacturing` pack (`materials`, `manufacturing-processes`, `characterization`, `mechanical-testing`, `fatigue`, `fea-methods`), `phenotyping`, `geodesy` |
| L2: one program, format, source or facility | how one tool or data source behaves | `abaqus` (with Tosca), `morphorm`, `slurm`, `hdf5`, `adios`, `parquet`, `ndp`, `earthscope`, `appl-core` |
| L3: one instance | IDs, file names, counts, measured values from a run | never shipped; discovered at runtime, asked, or recorded with the data |

Rules:
- **A method bundle never contains a program.** `manufacturing` teaches
  finite-element and topology-optimization method. `abaqus` and `morphorm` are
  separate L2 plugins that an agent selects. Their fragments describe what each
  program can do, and none claims to be the default.
- **An agent's own process belongs to the agent's plugin.** Factorio's dossier,
  consultation and review skills live in `factorio`, not in `scientific-method`.
- **A subagent declares the plugins whose skills its prompt references** and gets
  the tools its job needs. At least it can read files; an engineer can also write
  and run them.
- **Every plugin with domain content carries `.lint-l3` and `lint-denylist.txt`**,
  so `scripts/check_skill_literals.py` guards it.
- **Fragments stay within 150 tokens.** Longer guidance becomes a skill.
- **A subagent receives its owner plugin's fragments too.** Gate an agent's
  main-only fragments (mission, roster, practice) with
  `when: {"tools": [<a tool only the main agent has>]}` so its subagents do not
  read the main agent's mission as their own.

## The agents

| Agent | Identity | Composition (beyond its base) | Level |
|---|---|---|---|
| `standard` (CLIO) | the general workspace assistant | workspace, shell, web, documents, visuals, connected-data, delegation, orchestration | L0 |
| `science` (CLIO Science) | base for the science agents | standard + `scientific-method` | L0 |
| `deep-researcher` | cited web research with independent verification | `deep-research` (only its researcher and critic subagents carry `web`) | L0 |
| `document-production` | documents in every office and publishing format | `document-production` (with review) | L0 |
| `clio-search` | answers from CLIO's own conversations and files | `clio-search` | L0 |
| `clio-data` | inspects, converts and validates scientific data files | science + `clio-data`, `data-onboarding`, `hdf5`, `adios`, `parquet` | L2 formats |
| `factorio` | manufacturing and materials research partner | science + `manufacturing` pack + `abaqus`, `morphorm`, `slurm` + `factorio` | L1 domain, L2 programs |
| `earthscope` | EarthScope GNSS analysis through NDP | science + `geodesy`, `geo`, `ndp` + `earthscope` | L2 source |
| `appl-core` (OPAL) | APPL-CORE plant-phenotyping exports | science + `data-onboarding`, `phenotyping`, `parquet` + `appl-core` | L2 source (export version 6) |
| `spotter-ai` (SPOTTER) | forensic watcher over a working CLIO session | `spotter` (provenance and attention tools; alerts and containment through CLIO) | L0 |

## Removed

These were removed from the plugin-era marketplace (2026-10):
- the blueprint-era demos `genomics-review`, `geospatial-field-review`,
  `hpc-io-regression`, `materials-crystal-review`, `ndp-environmental-hazards`,
  `proteomics-mzml-review`, `remote-sensing-ogc-review`,
  `seismic-waveform-review`, `terrain-suitability` and `wildfire`;
- `phenotype`, the synthetic workload that APPL-CORE (OPAL) replaces;
- `data-semantics` and `format-bridge`, folded into `clio-data`;
- `topology`, split into `fea-methods` (method) and `abaqus` / `morphorm`
  (programs).

## Open follow-ups

- Most L1 skills in the `manufacturing` pack are short checklists. They should
  gain procedures, references and bundled scripts, written with the domain
  owners.
- Behavioral evals that swap the instance (L3) and the source or program (L2)
  for `earthscope`, `factorio` and `clio-data`, as `appl-core` already has.
- The `earthscope-stations` catalog is a generic "pick points on a map" pattern
  and belongs in CLIO's core catalog as a preset.
- In clio-agent: `core.tasks` takes about 2.5k tokens of every prompt, and the
  `fleet.models` fragment names spawn and flow tools that some agents lack.
