# earthscope-single-agent

A single tier-1 EarthScope GNSS scientist that loads focused skills on demand:
region resolution, station acquisition (with an interactive station-selection
surface), analysis, visualization, coverage comparison with optional regional
fanout, and reporting.

## Pack tree

```
earthscope-single-agent/
├── AGENT.md                              # blueprint manifest (root_expert: main)
├── README.md                             # this file
├── catalogs/
│   └── earthscope-stations/              # this pack's own A2UI catalog (S7)
│       ├── catalog.json                  # official 0.9.1 catalog-file shape
│       ├── catalog.clio.json             # CLIO packaging sidecar
│       └── instructions.md               # producer recipe + one worked example
├── experts/
│   └── main.md                           # the single react expert
├── skills/
│   ├── resolve-earthscope-region.md
│   ├── acquire-earthscope-gnss/SKILL.md  # station discovery, ranking, staging
│   ├── analyze-earthscope-gnss/SKILL.md
│   ├── visualize-earthscope-gnss/SKILL.md
│   ├── compare-earthscope-coverage/SKILL.md
│   ├── delegate-earthscope-region/SKILL.md
│   └── write-earthscope-report/SKILL.md
└── tests/
    └── test_a2ui_catalog_pack.py         # composability proof for the catalog above
```

## Custom A2UI catalogs

A marketplace pack is not limited to the renderer's built-in Basic and
CLIO-workspace A2UI components — it can ship its own catalog, declared in the
blueprint and installed together with the pack, with no clio-agent or
gact-tui source change required. This pack's `catalogs/earthscope-stations/`
is a worked example: it aliases the renderer's existing `clio.map.v1` kernel
under the name `StationMap` and the `ChoicePicker` kernel (locked to
`variant: "multipleSelection"`) under `StationPicker`, alongside the Basic
`Text`/`Column`/`Row`/`Button` components, and declares one domain event,
`earthscope.stations.selected`.

To add your own catalog:

1. **Ship three files** at `<pack>/catalogs/<name>/`:
   - `catalog.json` — the official A2UI 0.9.1 catalog-file shape (mirror
     clio-schemas' `catalogs/basic/catalog.json`): `$schema`, `$id`, `title`,
     `description`, `catalogId`, `components` (one JSON Schema per component,
     with a `component: {"const": "<Name>"}` discriminator), `functions`
     (client-callable checks/formatters — copy the Basic catalog's 14 unless
     you need your own), and `$defs` (at minimum `theme` and `anyComponent`,
     which `server_to_client.json` resolves via `catalog.json#/$defs/...`).
     Component names should be valid UAX#31 identifiers (a non-identifier
     name is a warning, not a hard error, in 0.9.1).
   - `catalog.clio.json` — the CLIO packaging sidecar (never sent on the A2UI
     wire): `catalogId`, `protocolVersion: "0.9.1"`, `trust: {"source":
     "pack"}`, `implements` (one entry per component you declared, naming the
     renderer `kernel` it aliases — every kernel MUST be a component the
     Basic or clio-workspace catalog already implements, plus optional
     `presets` that lock a property to a fixed value), and any `events` your
     components dispatch (`destination: "agent"` for an ordinary domain
     event; `"permission"`/`"run"` route elsewhere and `"run"` requires an
     `operation`).
   - `instructions.md` — producer guidance: the recipe for composing your
     components together, at least one complete worked example
     (`createSurface`/`updateComponents`/`updateDataModel`), and any rules
     specific to your domain (e.g. "ids come only from observed tool
     evidence").
2. **Declare it in `AGENT.md`'s frontmatter**:
   ```yaml
   a2ui_catalogs:
     <name>: catalogs/<name>
   ```
   If your catalog needs runtime pieces newer than the widest clio-agent
   version your pack otherwise supports (e.g. a specific campaign slice),
   declare the floor as a PEP 440 specifier — `requires: {clio_agent:
   ">=0.9.5"}` — so an older runtime refuses to activate the pack instead of
   installing a catalog it cannot serve.
3. **Declare it on the expert(s) that use it** (`experts/<id>.md`):
   ```yaml
   a2ui_catalogs:
     - <name>
   ```
   and point that expert's A2UI-usage prose at the generated catalog skill
   `a2ui-catalog-<name>` (the runtime turns every installed catalog into a
   progressive-disclosure skill automatically — you never write that
   skill's body yourself, and you never need to add it to the expert's
   `skills:` list).
4. **Prove it** with a test mirroring
   `tests/test_a2ui_catalog_pack.py`: `catalog.json` validates as
   `clio_schemas.a2ui.v0_9_1.catalog_file.CatalogFile`, `catalog.clio.json`
   validates as `clio_schemas.a2ui.sidecar.CatalogSidecar`, every
   `implements[*].kernel` names a Basic or clio-workspace component, and your
   `instructions.md`'s worked example validates against the catalog with
   `clio_schemas.a2ui.validation.message_validator("server_to_client",
   catalog=...)` / `catalog_validators(...)`. Then run
   `scripts/validate_marketplace_blueprints.py` (needs a clio-agent
   checkout — see that script's own docstring) to exercise the same
   install-time gate the live server runs.

No renderer code, tool code, or protocol change is required on the clio-agent
or gact-tui side: the client already knows how to render any catalog it is
sent, and the producer tools (`create_a2ui_surface` and friends) accept any
component the negotiated catalog declares.
