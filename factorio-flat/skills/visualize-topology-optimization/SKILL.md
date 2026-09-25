---
name: visualize-topology-optimization
title: Visualize a Topology Optimization Run
description: Show a Tosca or Abaqus topology optimization the way scientists inspect it, before and after with a stress toggle, and the design history with density and cycle sliders. Use once optimization output exists.
---

This skill uses the exporter and renderer from `abaqus-visualization` (load
it too) and the two views in the `a2ui-catalog-abaqus-topology` catalog
skill. It does not run Abaqus or Tosca.

## 1. Find the evidence

In the run directory the scientist or a previous step named, locate:

- the baseline result: the first design cycle's ODB or the plain FEA job;
- Tosca's `TOSCA_POST/ISO_SMOOTHING.stl`, and the `ISO_VALUE` in the `.par`
  file that produced it;
- the design cycles in one ODB. Merge them with `mdb.CombineOptResults`
  inside `abaqus cae noGUI=...` if the run did not; each frame is then one
  cycle, with the element density as `MAT_PROP_NORMALIZED`;
- the last cycle's ODB with stresses (the re-analysis run scripts write,
  for example `SAVE.inp/<last>/…_optimized.odb`);
- `optimization_report.csv` for the objective and constraint per cycle.

If only geometry exists, say that stress is not available and build the
comparison without the toggle.

## 2. Export

Run these the way `abaqus-visualization` describes: the `odb_to_glb.py` steps
under `abaqus python` next to the ODBs (with `fea_glb.py` copied alongside),
the `fea_glb.py` step through `uv run --no-project --with "numpy>=1.24"`.

```text
# before: the baseline part with stresses
abaqus python odb_to_glb.py BASELINE.odb -o baseline.glb --stage baseline

# design history: every element face, density for every cycle
abaqus python odb_to_glb.py COMBINED.odb -o design.glb --stage optimized --cells --frames all --frame-label Cycle

# after: the last cycle at the iso level as the stress source, then Tosca's surface
abaqus python odb_to_glb.py LAST_CYCLE.odb -o optimized_fe.glb --stage optimized --iso ISO_VALUE
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/fea_glb.py" stl ISO_SMOOTHING.stl -o optimized.glb --stage optimized --project-from optimized_fe.glb
```

Here `SKILL_ROOT` is the `abaqus-visualization` skill's directory, where the
scripts live.

Check the smoothed surface before showing it. Compare the enclosed volume and
bounding box printed for `optimized.glb` with the design domain: an iso
surface that kept only the frozen regions, or pieces with no material between
them, means the smoothing level or cycle is wrong. The design-history view
makes this visible at a glance (raise the density slider and watch whether
the load path survives), so show it and report the finding instead of
presenting a disconnected part as the result.

## 3. Present

Register `baseline.glb`, `optimized.glb`, and `design.glb` as artifacts. Then
build the two views from the catalog skill:

- **`topology-compare`**: before and after, linked, with the stress
  `CheckBox`, retained volume, peak nodal stress, and accept/revise buttons.
- **`topology-history`**: the design mesh with the density slider (start at
  `ISO_VALUE`), the cycle slider (start at the last cycle), the convergence
  plot from `optimization_report.csv`, and "Use this view in the report".

Retained volume comes from `optimization_report.csv` (last cycle over cycle
0). Peak stresses are the printed `S_MISES` maxima, labeled as nodal surface
values: Tosca evaluates its stress constraint differently, so they are not
proof that the constraint held.

When `abaqus.topology.figure-requested` arrives, render that exact view with
`render_view.py` (run as `abaqus-visualization` shows, with `--field DENSITY
--frame FRAME --threshold DENSITY:ISO:1 --camera 'CAMERA_JSON'`), register
the PNG, and cite it. When
`abaqus.topology.reviewed` arrives, accept moves on to re-verification and
revise asks what to change in the formulation.

## 4. Say what the views show

State in words where material was removed, where stress concentrates after
optimization, and how the density field settled over the cycles. Say what the
views cannot tell: the optimized stresses come from the last design cycle's
density-penalized model, projected onto the smoothed surface, so the design
still needs a clean remesh of the smoothed geometry and its own FE check
(`finite_element_analysis`) before any fatigue claim.
