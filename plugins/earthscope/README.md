# earthscope

The L2 source plugin behind the `earthscope` agent (`agents/earthscope.py`):
its mission and views fragments, `acquire-earthscope-gnss` (finding and
staging EarthScope GNSS station catalogs and position series through the
National Data Platform), the typed `workflow_state` vocabulary, and this
plugin's own A2UI catalog. The GNSS methods (time series, station catalogs,
regions, coverage comparison) live in the `geodesy` plugin, which works for
any network.

```
earthscope/
├── plugin.json                         # Agent Plugins 1.0.0 manifest, workflow_state
├── skills/acquire-earthscope-gnss/     # the EarthScope source skill
├── ai.iowarp.clio/
│   ├── prompt/                         # mission and views fragments
│   └── a2ui/earthscope-stations/       # this plugin's A2UI catalog
└── tests/test_a2ui_catalog.py          # composability proof for the catalog
```

## Shipping an A2UI catalog in a plugin

A plugin can ship its own catalog with no clio-agent or gact-tui change. Put
three files in `ai.iowarp.clio/a2ui/<name>/`; the folder is the declaration:

- `catalog.json`: the official A2UI 0.9.1 catalog-file shape (`$schema`, `$id`,
  `title`, `description`, `catalogId`, `components` with a
  `component: {"const": "<Name>"}` discriminator, `functions`, and `$defs` with
  at least `theme` and `anyComponent`).
- `catalog.clio.json`: the CLIO packaging sidecar, never sent on the wire:
  `catalogId`, `protocolVersion: "0.9.1"`, `trust`, `implements` (the renderer
  `kernel` each component aliases, which must be a Basic or clio-workspace
  component, plus optional `presets`), and the `events` components dispatch.
- `instructions.md`: producer guidance with at least one complete worked
  example (`createSurface`/`updateComponents`/`updateDataModel`).

This catalog aliases `clio.map.v1` as `StationMap` and `ChoicePicker` (locked to
`variant: "multipleSelection"`) as `StationPicker`, alongside Basic
`Text`/`Column`/`Row`/`Button`, and declares the `earthscope.stations.selected`
event. CLIO turns every resolved catalog into the progressive-disclosure skill
`a2ui-catalog-<name>`; point prompts at that skill instead of restating
component props. Prove a new catalog with a test like
`tests/test_a2ui_catalog.py` and `clio-agent plugin check`.
