---
name: geometry-to-glb
title: Geometry to GLB
description: Use when a 3D surface, mesh or point cloud (text triplets, PLY) should be looked at, to convert it to a .glb for the 3D mesh viewport.
keywords:
- level:L0
- 3d
- visualization
---

# Geometry to GLB

`scripts/to_glb.py` writes a glTF binary in the `clio.fea-mesh.v1` layout
that the `clio.mesh-viewport.v1` component reads: one indexed triangle mesh,
per-vertex fields described in the file's metadata, and the length unit.

It runs through uv's shared cache (`SKILL_ROOT` is the path that
`load_skill` reported):

```text
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/to_glb.py" mesh --vertices V.txt --faces F.txt [--colors C.txt] -o OUT.glb --units mm --stage LABEL
uv run --no-project --with "numpy>=1.24" --with trimesh python "SKILL_ROOT/scripts/to_glb.py" ply SURFACE.ply -o OUT.glb --units mm
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/to_glb.py" info OUT.glb
```

## What the input needs to say

- **The geometry's documentation** (format docs, manifest, column catalog)
  says which files are the surface (vertices + faces) versus raw points;
  whether face indices are zero- or one-based (the script auto-detects and
  reports `index_base_detected`; `--index-base` sets it from the docs); the
  length unit; and whether colours encode segmentation (a few distinct
  colours) or appearance (many).
- **Consistent geometry** has a vertex count equal to the colour rows, face
  indices in range, and a bounding box (printed as `bounds`) of plausible size
  in the stated unit for the object it shows. An object a hundred times too
  big or small is a unit problem; rescaling it silently hides that.
- **Authoritative geometry** is the source data. Viewer-only files
  (downsampled or normalised copies made for another app) are display copies.

## Output

- `COLOR_0` carries the vertex colours for any glTF viewer.
- The mesh viewport colours by **fields**, not vertex colours, so distinct
  colours also become a `SEGMENT` node field (one integer per colour, palette
  in the metadata as `segments.palette_rgb255`). With more than 256 distinct
  colours the input is shading, not segmentation, and no field is written.
- The script prints the metadata (counts, bounds, fields with min/max); it is
  the only source for numbers shown next to a view.

## Show it

A registered `.glb`'s `artifact://` id goes in a `clio.mesh-viewport.v1`
component (the clio-workspace catalog skill has its exact props): `field:
"SEGMENT"` colours by segment; two viewports that share a `syncGroup` orbit
together and share one colour range, which is how to compare the same object
at two times or under two treatments.

## Limitations

- **Point clouds are not shown by the viewport yet** (it renders triangles
  only). `points`/`pcd` inputs are refused unless `--allow-points`, which
  writes a plain glTF POINTS file for other viewers; the clio view is
  unavailable for them, and a surface made up from points is not the data.
- Only ASCII `.pcd` is read; binary PCD is refused.
- Quads are split into triangles; degenerate triangles are dropped and
  counted in `conversion`.
- One mesh per file, one frame; a time series is several files shown in
  synced viewports.
