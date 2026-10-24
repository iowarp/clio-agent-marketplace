#!/usr/bin/env python3
"""Summarize an Exodus II file as one JSON object (mesh checks without writing a new script).

Usage:  python3 exo_summary.py MESH.exo [--expect KEY=VALUE ...]

Reports: node/element counts; per block its name, element type and element count; node-set and side-set names
with sizes; the coordinate bounding box; time steps; nodal / element variable names; and, when the file has time
steps, min/max of each nodal variable at the last step. With --expect, each KEY=VALUE is compared against the
report (keys: num_nodes, num_elem, num_blocks, block:<name>:type, block:<name>:elems, nodeset:<name>,
sideset:<name>, bbox_min, bbox_max (comma-separated), time_steps) and the exit code is 1 if any differs.

Needs numpy and netCDF4 (source the packet's approved software loader first if `import netCDF4` fails).
"""
import json
import sys


def _names(ds, var):
    if var not in ds.variables:
        return []
    import numpy as np
    out = []
    for row in ds.variables[var][:]:
        row = np.ma.filled(row, b"")
        out.append(b"".join(bytes(x) for x in row if bytes(x) not in (b"", b"\x00")).decode(errors="replace").strip())
    return out


def summarize(path):
    import netCDF4
    import numpy as np
    ds = netCDF4.Dataset(path)
    dim = lambda n: ds.dimensions[n].size if n in ds.dimensions else 0
    rep = {"file": path, "num_nodes": dim("num_nodes"), "num_elem": dim("num_elem"), "num_dim": dim("num_dim")}
    coords = [ds.variables[c][:] for c in ("coordx", "coordy", "coordz") if c in ds.variables]
    if coords:
        rep["bbox_min"] = [float(np.min(c)) for c in coords]
        rep["bbox_max"] = [float(np.max(c)) for c in coords]
    blk_names = _names(ds, "eb_names")
    blocks = []
    for i in range(dim("num_el_blk")):
        v = ds.variables.get(f"connect{i + 1}")
        blocks.append({"name": blk_names[i] if i < len(blk_names) else "", "type": getattr(v, "elem_type", "") if v is not None else "",
                       "elems": int(v.shape[0]) if v is not None else 0, "nodes_per_elem": int(v.shape[1]) if v is not None else 0})
    rep["blocks"] = blocks
    ns_names = _names(ds, "ns_names")
    rep["nodesets"] = {(ns_names[i] if i < len(ns_names) and ns_names[i] else f"#{i + 1}"): dim(f"num_nod_ns{i + 1}") for i in range(dim("num_node_sets"))}
    ss_names = _names(ds, "ss_names")
    rep["sidesets"] = {(ss_names[i] if i < len(ss_names) and ss_names[i] else f"#{i + 1}"): dim(f"num_side_ss{i + 1}") for i in range(dim("num_side_sets"))}
    rep["time_steps"] = dim("time_step")
    if "time_whole" in ds.variables and rep["time_steps"]:
        t = ds.variables["time_whole"][:]
        rep["time_first_last"] = [float(t[0]), float(t[-1])]
    nod = _names(ds, "name_nod_var")
    rep["nodal_vars"] = nod
    rep["elem_vars"] = _names(ds, "name_elem_var")
    if nod and rep["time_steps"]:
        last = {}
        for i, n in enumerate(nod):
            var = ds.variables.get(f"vals_nod_var{i + 1}")
            if var is None and "vals_nod_var" in ds.variables:
                arr = ds.variables["vals_nod_var"][-1, i, :]
            elif var is not None:
                arr = var[-1, :]
            else:
                continue
            last[n] = [float(np.min(arr)), float(np.max(arr))]
        rep["nodal_min_max_last_step"] = last
    ds.close()
    return rep


def check(rep, expects):
    bad = []
    blocks = {b["name"]: b for b in rep["blocks"]}
    for e in expects:
        k, _, v = e.partition("=")
        if k.startswith("block:"):
            _, name, field = k.split(":", 2)
            got = blocks.get(name, {}).get(field)
        elif k.startswith("nodeset:"):
            got = rep["nodesets"].get(k.split(":", 1)[1])
        elif k.startswith("sideset:"):
            got = rep["sidesets"].get(k.split(":", 1)[1])
        elif k in ("bbox_min", "bbox_max"):
            want = [float(x) for x in v.split(",")]
            got = rep.get(k)
            ok = got is not None and len(got) == len(want) and all(abs(a - b) <= 1e-9 * max(1.0, abs(b)) for a, b in zip(got, want))
            bad += [] if ok else [{"key": k, "expected": want, "got": got}]
            continue
        else:
            got = rep.get(k)
        if str(got) != v:
            bad.append({"key": k, "expected": v, "got": got})
    return bad


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path, rest = sys.argv[1], sys.argv[2:]
    expects = [a for a in rest if a != "--expect"]
    rep = summarize(path)
    if expects:
        rep["expect_failures"] = check(rep, expects)
        rep["expect_ok"] = not rep["expect_failures"]
    print(json.dumps(rep, indent=1))
    sys.exit(1 if expects and rep["expect_failures"] else 0)
