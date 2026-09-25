---
name: abaqus-visualization
title: Visualize Abaqus Geometry and Results
description: Show any Abaqus-generated geometry or result (.inp mesh, .odb fields, Tosca STL) as an interactive 3D view or a report figure. Use whenever a model, mesh, or solver result should be looked at rather than described.
---

Scientists read FEA output by looking at it: turning the part, coloring it by a
result, hovering to read a value, cutting it open. This skill turns Abaqus and
Tosca files into meshes the CLIO 3D viewport shows, and into PNG figures for
reports. It does not run Abaqus; it starts from files a run already wrote.

## The files and how to run them

Resolve this skill's directory as `SKILL_ROOT`. `scripts/` holds three tools
that stay side by side:

| Script | Runs in | Reads |
| --- | --- | --- |
| `odb_to_glb.py` | `abaqus python` (Abaqus 2024 or newer, Python 3) | an ODB: mesh, S (von Mises), U, PEEQ, Tosca density, one or all frames |
| `fea_glb.py` | `uv run` with numpy | a flattened `.inp` mesh, a Tosca STL, or another `.glb` to project from |
| `render_view.py` | `uv run` with numpy and matplotlib | a `.glb`, to draw a report figure |

Run the two plain-Python tools through uv's shared cached environment, never
a `.venv` inside the installed skill or blueprint directory:

```text
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/fea_glb.py" ARGS
uv run --no-project --with "numpy>=1.24" --with "matplotlib>=3.8" python "SKILL_ROOT/scripts/render_view.py" ARGS
```

`odb_to_glb.py` needs Abaqus's own interpreter, which brings its own numpy:
`abaqus python "SKILL_ROOT/scripts/odb_to_glb.py" ARGS`. It imports
`fea_glb.py` from its own directory, so when the ODB lives on another machine
(a cluster login node), copy both files there together and run it next to the
ODB; bring back only the `.glb`.

All three share one format, `clio.fea-mesh.v1`: a glTF binary with the mesh,
node and cell fields, and optional frames (increments, design cycles). Every
command prints the file's metadata, including each field's `min`/`max`; keep
that output, because it is the only source for numbers you put next to a view.
`fea_glb.py info FILE.glb` prints it again later.

## Choose the export

- **A part or a result to look at**: a surface export, the outer faces only,
  small and smooth. `odb_to_glb.py Job.odb -o job.glb --stage baseline`, or
  `fea_glb.py inp model.inp -o model.glb --stage baseline` for geometry
  without results. Hierarchical `.inp` files (with
  `*Part`/`*Instance`) go through the ODB instead; `fea_glb.py` refuses them.
- **Something to threshold or look inside**: a cells export (`--cells`), which
  keeps every element face so the viewer can hide elements by a cell field and
  rebuild the surface. Larger; use it when the scientist will filter.
- **A quantity over increments or cycles**: add `--frames all` (and
  `--frame-label Increment` or `Cycle`). The viewer's `frame` then steps
  through them.
- **A smoothed surface with results on it**: `fea_glb.py stl surface.stl -o
  out.glb --stage optimized --project-from fe.glb` carries node fields from
  the FE export onto the STL by nearest surface node.

## Show it

Register each `.glb` as an artifact and use the returned `artifact://` id.
For a general view, build a `clio.mesh-viewport.v1` surface from the
clio-workspace catalog (its catalog skill has the property reference):

- `field` picks the coloring (`S_MISES` in MPa, `U_MAG` in mm, `PEEQ`,
  `DENSITY` from 0 to 1), and
  `showField` bound to a `CheckBox` toggles it.
- `thresholdField` with `thresholdMin`/`thresholdMax`, bound to
  `clio.slider.v1` sliders (they take a `step` and a typed value; the Basic
  `Slider` only moves in whole numbers), keeps only the cells in range.
- `frame`, bound to a `clio.slider.v1` with `step: 1`, steps through frames.
- Views that share a `syncGroup` orbit together and share one color scale.
  Use one group whenever two views are compared.

For topology optimization results, use `visualize-topology-optimization`
instead; it builds on this skill with ready-made views.

## Report figures

The viewport's own "Save image" button gives the scientist a PNG of what they
see. For a figure you cite, render it yourself from the same file:

```text
uv run --no-project --with "numpy>=1.24" --with "matplotlib>=3.8" python "SKILL_ROOT/scripts/render_view.py" job.glb -o figure.png --field S_MISES --range 0:170 --camera '<camera JSON from the event>' --title "Baseline, 20 kN"
```

When the surface binds `camera` to a path and a button sends it, use that
camera exactly, with the same field, frame, threshold, and color range the
view showed (pass the shared range with `--range` so figures of compared
states use one scale). Without a camera, `--preset iso|front|side|top`.

## Say what the view is

Name the field, unit, frame, and averaging in words: stresses are
element-nodal values averaged at nodes (Abaqus/CAE's "Avg: 100%"), so peaks
at notches read lower than integration-point values. Projected fields on a
smoothed STL are nearest-node copies from the FE mesh, not a new solve. A view
never replaces the numbers the scientist asked for; it shows where they are.
