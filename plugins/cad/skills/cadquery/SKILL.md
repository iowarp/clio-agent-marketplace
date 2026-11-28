---
name: cadquery
description: Use when a part should be modeled in CAD with CadQuery, such as a wing section, a duct, a vehicle body or a bracket, and exported as STEP or STL, for example as geometry for a simulation. Gives the run command that works on CLIO's own Python the first time, and the export checks.
keywords: [cad, cadquery, step, stl, geometry, level:L2]
---

# CadQuery modeling

A part modelled as a script in the workspace can be read, changed by one
dimension and run again. CadQuery is pip-installable; nothing is installed
by hand.

## Run it on CLIO's Python

The uv and the Python CLIO brings with it run the script:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" --with "cadquery>=2.8" --with trimesh python model.py
```

In PowerShell:

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON --with "cadquery>=2.8" --with trimesh python .\model.py
```

- The floor `cadquery>=2.8` is what makes it resolve. CadQuery 2.8
  resolves to a cadquery-ocp with wheels for Python 3.11 to 3.14. Releases up to
  2.6 need cadquery-ocp 7.8, which has no wheels for Python 3.14, so on a 3.14
  CLIO Python uv stops with "No solution found" before the script runs.
- If uv still cannot resolve, its hint names the Python ABI it needed;
  `--python 3.12` resolves it, and the model is not the cause.
- The first run downloads OCP and VTK, several hundred MB, which a command
  timeout under 600 s can cut off; later runs reuse uv's cache.

## Model

- CadQuery has no units: a script is in whatever unit it is consistently
  written in (mm is the STEP and STL convention), and what +X, +Y and +Z mean
  for the part is known only if stated.
- Design dimensions as named constants at the top of the script make a change
  one edit.
- Build solids from closed profiles: points through `polyline` or `spline`, then
  `close()`, then `extrude`, `loft`, `revolve` or `sweep`. A profile that does
  not close gives a face or nothing, not a solid.
- Angles and placement as explicit `rotate` and `translate` steps after the
  shape is built stay checkable; the bounding box after each shows where the
  part went.

## Export and check

- STEP carries the exact geometry and STL the mesh a solver or a viewer
  reads: `cq.exporters.export(shape, "part.step")` and
  `cq.exporters.export(shape, "part.stl", tolerance=..., angularTolerance=...)`.
  A smaller tolerance gives a finer STL, so the tolerance is part of what the
  STL is.
- `isValid()`, the volume and the bounding box check the solid. The STL read
  back with trimesh shows whether it is watertight with consistent winding, its
  triangle count and its bounding box against the intended dimensions.
- A copy in a solver's own frame (an immersed-boundary grid, a mesher's
  domain), as a separate file with its transform recorded, leaves the design
  file as the person specified it.

## Hand it over

- `create_artifact` registers the STL and the STEP (purpose `deliverable`, the
  script in `used`). CLIO opens a registered STL or STEP in its 3D view; a file
  only written to the workspace shows nowhere. A solver-frame copy is an
  `intermediate`.
- The `geometry-to-glb` skill is only for a mesh with per-vertex fields shown in a
  `clio.mesh-viewport.v1` component. A part needs no conversion to be seen.
