---
name: cadquery
description: Use when a part should be modeled in CAD with CadQuery, such as a wing section, a duct, a vehicle body or a bracket, and exported as STEP or STL, for example as geometry for a simulation. Gives the run command that works on CLIO's own Python the first time, and the export checks.
keywords: [cad, cadquery, step, stl, geometry, level:L2]
---

# CadQuery modeling

Model the part as a script in the workspace, so the person can read it, change a
dimension and run it again. CadQuery is pip-installable; nothing is installed
by hand.

## Run it on CLIO's Python

Run the script with the uv and the Python CLIO brings with it:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" --with "cadquery>=2.8" --with trimesh python model.py
```

In PowerShell:

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON --with "cadquery>=2.8" --with trimesh python .\model.py
```

- Keep the floor `cadquery>=2.8` and do not pin an older release. CadQuery 2.8
  resolves to a cadquery-ocp with wheels for Python 3.11 to 3.14. Releases up to
  2.6 need cadquery-ocp 7.8, which has no wheels for Python 3.14, so on a 3.14
  CLIO Python uv stops with "No solution found" before the script runs.
- If uv still cannot resolve, its hint names the Python ABI it needed. Rerun with
  `--python 3.12` instead of changing the model.
- The first run downloads OCP and VTK, several hundred MB. Give the command a
  timeout of at least 600 s; later runs reuse uv's cache.

## Model

- CadQuery has no units. Say which you use (mm is the STEP and STL convention),
  keep one throughout, and say what +X, +Y and +Z mean for the part.
- Keep the design dimensions as named constants at the top of the script, so a
  change is one edit.
- Build solids from closed profiles: points through `polyline` or `spline`, then
  `close()`, then `extrude`, `loft`, `revolve` or `sweep`. A profile that does
  not close gives a face or nothing, not a solid.
- Apply angles and placement as explicit `rotate` and `translate` steps after
  the shape is built, and print the bounding box after each.

## Export and check

- Export STEP for the exact geometry and STL for the mesh a solver or a viewer
  reads, with `cq.exporters.export(shape, "part.step")` and
  `cq.exporters.export(shape, "part.stl", tolerance=..., angularTolerance=...)`.
  A smaller tolerance gives a finer STL; state the one you used.
- Before handing the STL on, check the solid with `isValid()` and report its
  volume and bounding box. Then read the STL back with trimesh and report
  whether it is watertight with consistent winding, its triangle count and its
  bounding box against the intended dimensions.
- When a solver needs the part in its own frame (an immersed-boundary grid, a
  mesher's domain), write that copy as a separate file and record the transform,
  so the design file stays as the person specified it.
- To show the part in CLIO's 3D view, convert the STL with the visuals plugin's
  `geometry-to-glb` skill.
