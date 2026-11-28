---
name: visualize-topology-optimization
title: Visualize a Topology Optimization Run
description: Use once Tosca or Abaqus topology optimization output exists, to show it before and after with a stress toggle and its design history with density and cycle sliders.
keywords:
- level:L2
- abaqus
---

This skill uses the exporter and renderer from `abaqus-visualization` and the
two views in the `a2ui-catalog-abaqus-topology` catalog skill. It does not
run Abaqus or Tosca.

## The evidence

A run directory (the one the scientist or a previous step named) holds:

- the baseline result: the first design cycle's ODB or the plain FEA job;
- Tosca's `TOSCA_POST/ISO_SMOOTHING.stl`, and the `ISO_VALUE` in the `.par`
  file that produced it;
- the design cycles in one ODB, or per-cycle ODBs that
  `mdb.CombineOptResults` inside `abaqus cae noGUI=...` merges; each frame is
  then one cycle, with the element density as `MAT_PROP_NORMALIZED`;
- the last cycle's ODB with stresses (the re-analysis run scripts write,
  for example `SAVE.inp/<last>/…_optimized.odb`);
- `optimization_report.csv` for the objective and constraint per cycle.

With only geometry there is no stress to show, and the comparison has no
stress toggle.

## Export

These run the way `abaqus-visualization` describes: the `odb_to_glb.py` steps
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

The smoothed surface can be wrong. The enclosed volume and bounding box
printed for `optimized.glb`, set against the design domain, show it: an iso
surface that kept only the frozen regions, or pieces with no material between
them, means the smoothing level or cycle is wrong. The design-history view
makes this visible at a glance (raising the density slider shows whether the
load path survives); a disconnected part is a finding, not the result.

## Present

The two views from the catalog skill take `baseline.glb`, `optimized.glb`,
and `design.glb` registered as artifacts:

- **`topology-compare`**: before and after, linked, with the stress
  `CheckBox`, retained volume, and peak nodal stress. Its accept/revise
  buttons belong to a design decision that is open now.
- **`topology-history`**: the design mesh with the density slider (from
  `ISO_VALUE`), the cycle slider (from the last cycle), the convergence
  plot from `optimization_report.csv`, and "Use this view in the report".

Retained volume comes from `optimization_report.csv` (last cycle over cycle
0). Peak stresses are the printed `S_MISES` maxima, labeled as nodal surface
values: Tosca evaluates its stress constraint differently, so they are not
proof that the constraint held.

`abaqus.topology.figure-requested` carries the exact view; `render_view.py`
(run as `abaqus-visualization` shows, with `--field DENSITY --frame FRAME
--threshold DENSITY:ISO:1 --camera 'CAMERA_JSON'`) reproduces it as a PNG to
register and cite. `abaqus.topology.reviewed` with accept means the design
goes on to re-verification; revise means the formulation changes.

A completed visualization is transcript content with its interpretation;
showing a result or offering an optional figure export asks nothing of the
person, and mesh controls and report buttons do not make a surface a
question. `ask_user(..., surface_id=...)` carries an actual question, with
the view as context and meaningful choices, through the interactive response
flow.

## What the views show

The views show where material was removed, where stress concentrates after
optimization, and how the density field settled over the cycles. What they
cannot tell: the optimized stresses come from the last design cycle's
density-penalized model, projected onto the smoothed surface, so the design
still needs a clean remesh of the smoothed geometry and its own FE check
(`finite-element-analysis`) before any fatigue claim.
