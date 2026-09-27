"""Render a viewport .glb to a PNG for reports, from the view the scientist chose.

Reads the same ``clio.fea-mesh.v1`` files the 3D viewport shows and applies
the same field, frame, and threshold rules, so a report figure matches what
was on screen. The camera comes from the viewport's ``camera`` binding (the
JSON the agent receives in an event), or from a named preset.

    python render_view.py design.glb -o figure.png --field DENSITY \\
        --frame 20 --threshold DENSITY:0.3:1 --camera camera.json
    python render_view.py baseline.glb -o before.png --field S_MISES \\
        --range 0:170 --preset iso --title "Before optimization"

Needs numpy and matplotlib (ordinary Python, not Abaqus Python).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fea_glb  # noqa: E402


def visible_triangles(mesh, fields, frame, threshold):
    """Mirror of the viewport's rule: returns ``(triangles, cell per triangle)``."""

    tri = mesh.triangles
    if mesh.topology == "cells":
        keep = np.ones(mesh.cells, dtype=bool)
        if threshold is not None and threshold[0].location == "cell":
            field, low, high = threshold
            values = field.values[min(frame, field.frames - 1)]
            keep = (values >= low) & (values <= high)
        a = mesh.cell_a[tri[:, 0]]
        b = mesh.cell_b[tri[:, 0]]
        in_a = (a >= 0) & keep[np.clip(a, 0, None)]
        in_b = (b >= 0) & keep[np.clip(b, 0, None)]
        shown = in_a != in_b
        return tri[shown], np.where(in_a, a, b)[shown]
    shown = np.ones(len(tri), dtype=bool)
    if threshold is not None and threshold[0].location == "node":
        field, low, high = threshold
        values = field.values[min(frame, field.frames - 1)][mesh.node_index[tri]]
        shown = ((values >= low) & (values <= high)).all(axis=1)
    return tri[shown], np.full(int(shown.sum()), -1)


def triangle_values(mesh, field, frame, triangles, cells):
    values = field.values[min(frame, field.frames - 1)]
    if field.location == "cell":
        return values[cells]
    return values[mesh.node_index[triangles]].mean(axis=1)


def view_angles(camera, up_axis):
    """matplotlib elevation/azimuth/roll from a viewport camera state."""

    position = np.asarray(camera["position"], dtype=float)
    target = np.asarray(camera["target"], dtype=float)
    d = position - target
    d /= np.linalg.norm(d) or 1.0
    # matplotlib's frame is z-up; rotate the model's up axis onto z first.
    order = {"z": (0, 1, 2), "y": (2, 0, 1), "x": (1, 2, 0)}[up_axis]
    x, y, z = d[order[0]], d[order[1]], d[order[2]]
    return np.degrees(np.arcsin(np.clip(z, -1, 1))), np.degrees(np.arctan2(y, x)), order


PRESETS = {"iso": (1.0, 0.6, 1.0), "front": (0.0, 0.0, 1.0), "side": (1.0, 0.0, 0.0), "top": (0.0, 1.0, 0.001)}


def render(path, output, field_name=None, frame=0, threshold=None, value_range=None,
           camera=None, preset="iso", up_axis="y", title=None, dpi=200):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    mesh, fields, meta = fea_glb.read_glb(path)
    by_name = {f.name: f for f in fields}
    cut = None
    if threshold:
        name, low, high = threshold
        if name not in by_name:
            raise SystemExit("threshold field %s is not in %s" % (name, path))
        cut = (by_name[name], low, high)
    triangles, cells = visible_triangles(mesh, fields, frame, cut)
    if camera is None:
        bmin, bmax = mesh.positions.min(axis=0), mesh.positions.max(axis=0)
        center = (bmin + bmax) / 2
        offset = np.asarray(PRESETS[preset])
        offset = {"y": offset, "z": offset[[0, 2, 1]], "x": offset[[1, 0, 2]]}[up_axis]
        camera = {"position": list(center + offset), "target": list(center)}
    elev, azim, order = view_angles(camera, up_axis)

    corners = mesh.positions[triangles][:, :, order]
    fig = plt.figure(figsize=(6, 6.6))
    ax = fig.add_subplot(111, projection="3d")
    poly = Poly3DCollection(corners, linewidths=0)
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    light = np.abs(normals @ np.array([0.35, 0.45, 0.82]))
    shade = (0.45 + 0.55 * light)[:, None]
    field = by_name.get(field_name) if field_name else None
    if field is not None:
        values = triangle_values(mesh, field, frame, triangles, cells)
        low, high = value_range or (field.values.min(), field.values.max())
        norm = matplotlib.colors.Normalize(low, high)
        rgba = plt.cm.turbo(norm(values))
        rgba[:, :3] *= shade
        poly.set_facecolor(rgba)
        mappable = plt.cm.ScalarMappable(norm=norm, cmap="turbo")
        bar = fig.colorbar(mappable, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02)
        bar.set_label("%s%s" % (field.label, " (%s)" % field.unit if field.unit else ""))
    else:
        poly.set_facecolor(np.hstack([np.tile([0.72, 0.75, 0.79], (len(corners), 1)) * shade,
                                      np.ones((len(corners), 1))]))
    ax.add_collection3d(poly)
    lo, hi = mesh.positions[:, order].min(axis=0), mesh.positions[:, order].max(axis=0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    frames = meta.get("frames") or []
    subtitle = frames[min(frame, len(frames) - 1)]["label"] if frames else ""
    if cut is not None:
        subtitle = ", ".join(x for x in (subtitle, "%s in [%g, %g]" % (cut[0].label, cut[1], cut[2])) if x)
    fig.suptitle(title or meta.get("stage", ""), fontsize=12, y=0.97)
    if subtitle:
        fig.text(0.5, 0.925, subtitle, ha="center", fontsize=9, color="#475569")
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"output": output, "triangles": int(len(triangles)), "frame": subtitle}


def _pair(text, count):
    parts = text.split(":")
    if len(parts) != count:
        raise argparse.ArgumentTypeError("expected %d colon-separated values" % count)
    return parts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("glb")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--field", help="field to color by, e.g. S_MISES or DENSITY")
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--threshold", help="FIELD:MIN:MAX, e.g. DENSITY:0.3:1")
    parser.add_argument("--range", help="MIN:MAX color range (use the viewport's shared range)")
    parser.add_argument("--camera", help="JSON file or inline JSON with position/target")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="iso")
    parser.add_argument("--up-axis", choices=("x", "y", "z"), default="y")
    parser.add_argument("--title")
    args = parser.parse_args(argv)
    threshold = None
    if args.threshold:
        name, low, high = _pair(args.threshold, 3)
        threshold = (name.upper(), float(low), float(high))
    value_range = tuple(float(v) for v in _pair(args.range, 2)) if args.range else None
    camera = None
    if args.camera:
        text = open(args.camera).read() if os.path.exists(args.camera) else args.camera
        camera = json.loads(text)
    result = render(args.glb, args.output, args.field and args.field.upper(), args.frame, threshold,
                    value_range, camera, args.preset, args.up_axis, args.title)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
