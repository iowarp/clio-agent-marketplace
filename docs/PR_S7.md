# PR description (draft, for the owner to use verbatim)

## Title

feat: ship the earthscope-stations A2UI catalog (S7)

## Summary

- EarthScope Skills ships its own A2UI 0.9.1 catalog
  (`earthscope-single-agent/catalogs/earthscope-stations/`) instead of
  depending on any clio-agent or gact-tui source change: `StationMap`
  aliases `clio.map.v1`, a multi-select `StationPicker` aliases
  `ChoicePicker` (locked to `variant: "multipleSelection"` — the catalog's
  own schema declares that a `const`, so the validator refuses any other
  value), and `Text`/`Column`/`Row`/`Button` are copied from the Basic
  catalog verbatim. The catalog delivers one structured domain event,
  `earthscope.stations.selected` (`searchId` + non-empty `stationIds`).
- `AGENT.md`/`experts/main.md` declare the catalog; the acquisition skill's
  station-selection step now uses the catalog's `StationMap`/`StationPicker`/
  `Button` recipe and `ask_user(..., surface_id="earthscope-stations")` in
  place of the old generic `ChoicePicker` + `agent.submit` flow.
- `earthscope-single-agent/tests/test_a2ui_catalog_pack.py` is the
  composability proof: the catalog file validates as clio-schemas'
  `CatalogFile`, the sidecar as `CatalogSidecar`, every `implements[*].kernel`
  names a Basic or clio-workspace component, the `instructions.md` worked
  example validates end to end against the catalog, and — the test that
  matters most for this PR — `clio_agent.gact.agent_blueprints.
  validate_agent_blueprint_path` (the REAL function the live GACT server
  runs at pack install/enable time, called directly, not reimplemented)
  reports zero errors and zero warnings for this pack.
- `earthscope-single-agent/README.md` gains a "Custom A2UI catalogs" section
  (how a pack author adds one); `CHANGELOG.md` records the change; the pack
  version bumps 0.2.3 → 0.3.0.

## CI: the new `a2ui-catalog-pack` job

`.github/workflows/ci.yml` gains a second job that runs
`test_a2ui_catalog_pack.py` against `clio-agent @ git+.../clio-agent@develop`
(clio-agent's own `uv` source pins `clio-schemas==0.3.1`, so the `clio_schemas
.a2ui` import this test needs resolves without a separate pin here). The
pre-existing `model-inheritance` job is deliberately untouched: it runs
`unittest discover` in a bare, dependency-free interpreter, so a
clio-agent-dependent test cannot live there.

**Verified state of this job against `origin/develop` today
(`a9d535ab1bec1a4367243c2c9d8bf9b9b3b0e675`): GREEN, 7/7 passed.** This
corrects an earlier assumption (mine, going into this PR) that the job would
be red until clio-agent's S4/S5 slices land on `develop`. That assumption
was wrong: `validate_agent_blueprint_path` is a STATIC validator — parsed
frontmatter, expert hierarchy, tool references, and (S2's contribution) the
pack's own `a2ui_catalogs` declaration: catalog/sidecar schema validity and
every `implements[*].kernel` resolving to a Basic or clio-workspace
component. S2 (`a2ui_catalogs/blueprint.py`, the catalog registry) is
already merged to `develop` via the S3 PR (#1373). What is genuinely still
missing from `develop` is S4 (`gact/a2ui_producer/` — the producer tools)
and S5 (`ask_user_tool.py`'s `surface_id` dispatcher correlation) — neither
of which `validate_agent_blueprint_path` exercises, because both are
*runtime* behavior, not structural pack validation. Those are covered by
clio-agent's own live composability test and the three-scene live gate
(S7 deliverables 4/5 in iowarp/clio-agent-marketplace#69), which are
explicitly **not** part of this PR and live in the clio-agent repository
instead.

So: this job is a real, currently-green regression gate for the static
catalog contract (it will go red if a future `develop` change breaks
catalog/sidecar validation, kernel-implements checking, or this pack's own
declaration) — not a gate blocked on S4/S5 landing. Merge order is otherwise
unaffected: this PR can land independently of the clio-agent S4/S5 PRs; nothing
here depends on their runtime pieces.

## Test plan

- `uv run --no-project python -m unittest discover -s tests -v` — 76 passed.
- `uv run --project <clio-schemas checkout> --with pytest --with jsonschema pytest earthscope-single-agent/tests/test_a2ui_catalog_pack.py` — 6 passed, 1 failed (expected: that one test needs `clio-agent` importable and fails loudly rather than skipping when it is not).
- `uv run --prerelease=allow --with "clio-agent @ git+https://github.com/iowarp/clio-agent@develop" --with pytest pytest earthscope-single-agent/tests/test_a2ui_catalog_pack.py -v` — 7 passed (the exact CI command).
- `uv run --no-project python scripts/check_model_pins.py .` — OK.
