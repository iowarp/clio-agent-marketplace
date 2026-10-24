---
name: geometry-to-glb
title: Geometry to GLB
description: Convert headerless text geometry (vertices/faces/colours triplets), PLY meshes, or point clouds into a .glb that clio's 3D mesh viewport can show, with per-vertex colour segments as a field. Use when a 3D surface or scan should be looked at rather than described.
keywords:
- level:L0
- 3d
- visualization
---

# Geometry to GLB

`scripts/to_glb.py` writes a glTF binary in the `clio.fea-mesh.v1` layout
that the `clio.mesh-viewport.v1` component reads: one indexed triangle mesh,
per-vertex fields described in the file's metadata, and the length unit.

Run it through uv's shared cache (substitute the `SKILL_ROOT` path that
`load_skill` reported):

```text
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/to_glb.py" mesh --vertices V.txt --faces F.txt [--colors C.txt] -o OUT.glb --units mm --stage LABEL
uv run --no-project --with "numpy>=1.24" --with trimesh python "SKILL_ROOT/scripts/to_glb.py" ply SURFACE.ply -o OUT.glb --units mm
uv run --no-project --with "numpy>=1.24" python "SKILL_ROOT/scripts/to_glb.py" info OUT.glb
```

## Before converting

1. **Find the geometry's documentation** (format docs, manifest, column
   catalog). Establish: which files are the surface (vertices + faces) versus
   raw points; whether face indices are zero- or one-based (the script
   auto-detects and reports `index_base_detected`; pass `--index-base` when
   the docs say); the length unit; and whether colours encode segmentation
   (a few distinct colours) or appearance (many). Tag each as stated/checked.
2. **Check before trusting**: vertex count equals colour rows; face indices
   are in range; the bounding box (printed as `bounds`) has a plausible size
   in the stated unit for the object it shows. An object a hundred times too
   big or small is a unit problem -- record it, do not rescale silently.
3. **Prefer authoritative geometry**. Viewer-only files (downsampled or
   normalised copies made for another app) are for display only; say so if
   you use them.

## Output

- `COLOR_0` carries the vertex colours for any glTF viewer.
- The mesh viewport colours by **fields**, not vertex colours, so distinct
  colours also become a `SEGMENT` node field (one integer per colour, palette
  in the metadata as `segments.palette_rgb255`). With more than 256 distinct
  colours the input is shading, not segmentation, and no field is written.
- The script prints the metadata (counts, bounds, fields with min/max); keep
  it -- it is the only source for numbers you put next to a view.

## Show it

Register the `.glb` as an artifact and use the returned `artifact://` id in a
`clio.mesh-viewport.v1` component (load the clio-workspace catalog skill for
its exact props): `field: "SEGMENT"` colours by segment; two viewports that
share a `syncGroup` orbit together and share one colour range, which is how to
compare the same object at two times or under two treatments.

## Limitations

- **Point clouds are not shown by the viewport yet** (it renders triangles
  only). `points`/`pcd` inputs are refused unless `--allow-points`, which
  writes a plain glTF POINTS file for other viewers; say that the clio view is
  unavailable rather than inventing a surface from points.
- Only ASCII `.pcd` is read; binary PCD is refused.
- Quads are split into triangles; degenerate triangles are dropped and
  counted in `conversion`.
- One mesh per file, one frame; a time series is several files shown in
  synced viewports.
