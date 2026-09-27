"""Export an Abaqus ODB's mesh and results as a viewport .glb.

Run with the Abaqus Python interpreter, next to ``fea_glb.py``::

    # outer surface with the last frame's S_MISES / U_MAG / PEEQ
    abaqus python odb_to_glb.py Job.odb -o baseline.glb --stage baseline

    # every element face, for thresholding in the viewer, with every frame
    abaqus python odb_to_glb.py Combined.odb -o design.glb --stage optimized \\
        --cells --frames all

For a Tosca topology run, merge the design cycles into one ODB first (one
frame per cycle) with ``mdb.CombineOptResults`` inside ``abaqus cae
noGUI=...``; the element density ``MAT_PROP_NORMALIZED`` then becomes the
``DENSITY`` cell field (0 to 1), one frame per cycle, and the viewer's
threshold slider and frame index do the rest.

``--iso`` (Tosca's ISO_VALUE, 0 to 1) keeps only elements at or above that
density in a surface export,
which is the stress source to project onto Tosca's smoothed STL
(``python fea_glb.py stl ISO_SMOOTHING.stl --project-from <that file>``).

Stresses are element-nodal values averaged at each node (the "Avg: 100%"
contour setting in Abaqus/CAE).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fea_glb  # noqa: E402

DENSITY_FIELDS = ("MAT_PROP_NORMALIZED", "DENSITY")


def _instance(odb, name):
    instances = odb.rootAssembly.instances
    if name:
        return instances[name]
    solid = [inst for key, inst in instances.items() if key != "ASSEMBLY" and len(inst.elements)]
    if len(solid) != 1:
        raise SystemExit(
            "ODB has %d meshed instances (%s); pass --instance"
            % (len(solid), ", ".join(instances.keys()))
        )
    return solid[0]


def _nodal_average(field_output, instance, node_row, invariant=None):
    """Average element-nodal values per node for one instance and frame."""

    from abaqusConstants import ELEMENT_NODAL, MISES  # Abaqus-only import

    subset = field_output.getSubset(region=instance, position=ELEMENT_NODAL)
    if invariant == "MISES":
        subset = subset.getScalarField(invariant=MISES)
    total = np.zeros(len(node_row))
    count = np.zeros(len(node_row))
    for block in subset.bulkDataBlocks:
        labels = np.asarray(block.nodeLabels)
        data = np.asarray(block.data).reshape(len(labels), -1)[:, 0]
        rows = np.fromiter((node_row[int(l)] for l in labels), dtype=np.int64, count=len(labels))
        np.add.at(total, rows, data)
        np.add.at(count, rows, 1.0)
    return np.divide(total, count, out=np.zeros_like(total), where=count > 0)


def _displacement(field_output, instance, node_row):
    u = np.zeros((len(node_row), 3))
    for value in field_output.getSubset(region=instance).values:
        u[node_row[value.nodeLabel]] = value.data[:3]
    return np.linalg.norm(u, axis=1)


def _density(frame, instance, cell_row):
    """Tosca's normalized density (0 to 1), one value per element."""

    for name in DENSITY_FIELDS:
        if name in frame.fieldOutputs.keys():
            out = np.ones(len(cell_row))
            for value in frame.fieldOutputs[name].getSubset(region=instance).values:
                row = cell_row.get(value.elementLabel)
                if row is not None:
                    out[row] = float(value.data)
            return out
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("odb")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--stage", required=True, choices=("baseline", "optimized"))
    parser.add_argument("--step", help="step name (default: last step)")
    parser.add_argument("--instance", help="instance name (default: the only meshed one)")
    parser.add_argument("--cells", action="store_true", help="export every element face")
    parser.add_argument("--frames", choices=("last", "all"), default="last")
    parser.add_argument("--frame-label", default="Frame", help='frame name prefix, e.g. "Cycle"')
    parser.add_argument("--iso", type=float, help="surface export: keep elements with density >= ISO")
    args = parser.parse_args(argv)
    if args.iso is not None and args.cells:
        parser.error("--iso applies to surface exports; a --cells export is thresholded in the viewer")

    from odbAccess import openOdb  # Abaqus-only import

    odb = openOdb(args.odb, readOnly=True)
    try:
        instance = _instance(odb, args.instance)
        step_name = args.step or odb.steps.keys()[-1]
        step_frames = odb.steps[step_name].frames
        chosen = list(step_frames) if args.frames == "all" else [step_frames[-1]]

        node_ids = np.asarray([n.label for n in instance.nodes], dtype=np.int64)
        coords = np.asarray([n.coordinates for n in instance.nodes], dtype=np.float64)
        node_row = {int(label): i for i, label in enumerate(node_ids)}
        elements, labels = [], []
        for element in instance.elements:
            family = fea_glb.element_family(str(element.type))
            if family:
                elements.append((family, tuple(element.connectivity[: fea_glb._CORNERS[family]])))
                labels.append(element.label)
        cell_row = {label: i for i, label in enumerate(labels)}

        series = {"S_MISES": [], "U_MAG": [], "PEEQ": [], "DENSITY": []}
        for frame in chosen:
            outputs = frame.fieldOutputs
            if "S" in outputs.keys():
                series["S_MISES"].append(_nodal_average(outputs["S"], instance, node_row, "MISES"))
            if "U" in outputs.keys():
                series["U_MAG"].append(_displacement(outputs["U"], instance, node_row))
            if "PEEQ" in outputs.keys():
                series["PEEQ"].append(_nodal_average(outputs["PEEQ"], instance, node_row))
            density = _density(frame, instance, cell_row)
            if density is not None:
                series["DENSITY"].append(density)

        keep = None
        if args.iso is not None:
            if not series["DENSITY"]:
                raise SystemExit("--iso given but no frame has %s" % " or ".join(DENSITY_FIELDS))
            keep = series["DENSITY"][-1] >= args.iso

        if args.cells:
            mesh = fea_glb.cell_mesh(node_ids, coords, elements)
        else:
            mesh = fea_glb.exterior_mesh(node_ids, coords, elements, keep=keep)
        fields = []
        for name, frames in series.items():
            if not frames or len(frames) != len(chosen):
                continue  # a result missing from some frames is not exported
            if name == "DENSITY" and not args.cells:
                continue
            fields.append(fea_glb.Field(name, np.vstack(frames)))
        frame_labels = ["%s %d" % (args.frame_label, f.frameId) for f in chosen]
        meta = fea_glb.write_glb(
            args.output, mesh, fields, stage=args.stage, frames=frame_labels,
            source={
                "kind": "odb", "path": os.path.abspath(args.odb), "step": step_name,
                "frames": [f.frameId for f in chosen], "instance": instance.name,
                "elements": len(elements), "iso": args.iso,
                "kept_elements": int(keep.sum()) if keep is not None else len(elements),
            },
        )
    finally:
        odb.close()
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
