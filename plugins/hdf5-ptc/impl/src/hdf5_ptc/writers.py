"""Write a selection to a new file: NetCDF-4 with provenance, or a VTK series for 3D views.

The NetCDF-4 subset keeps each variable's attributes and coordinate variables and adds
provenance attributes (source, selection, time written). The VTK form is a rectilinear
grid per time step with a ``.pvd`` index, so a 3D viewer opens it with real coordinates
and a time axis; the vertical coordinate can be mapped with ``z = scale * ln(ref / value)``
(log-pressure height, for example), since pressure levels are not evenly spaced.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import struct
from pathlib import Path
from typing import Any
from xml.sax.saxutils import quoteattr

import h5py
import numpy as np

from hdf5_ptc import cf
from hdf5_ptc.errors import refuse
from hdf5_ptc.selection import Selection, read


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _coord_subset(dataset: h5py.Dataset, sel: Selection) -> list[tuple[str, np.ndarray, dict]]:
    """``(name, values, attrs)`` of each axis's coordinate over the selection."""
    out = []
    for dim in cf.dimensions(dataset):
        axis = dim["axis"]
        name = dim.get("name") or f"dim{axis}"
        sl = sel.slices()[axis] if sel.start else slice(None)
        path = dim.get("coordinate")
        if path and path in dataset.file and dataset.file[path].ndim == 1:
            coord = dataset.file[path]
            out.append((name, np.asarray(coord[sl]), cf.attributes(coord)))
        else:
            idx = np.arange(dataset.shape[axis])[sl]
            out.append((name, idx, {}))
    return out


def write_netcdf(
    items: list[tuple[h5py.Dataset, Selection, str]], out: Path, source: str
) -> dict[str, Any]:
    """Write each ``(dataset, selection, name)`` as a variable of one NetCDF-4 file."""
    import h5netcdf  # noqa: PLC0415

    written = []
    with h5netcdf.File(out, "w") as nc:
        nc.attrs["Conventions"] = "CF-1.8"
        nc.attrs["history"] = f"{_now()} subset written by hdf5-ptc"
        nc.attrs["source"] = source
        for dataset, sel, name in items:
            coords = _coord_subset(dataset, sel)
            dim_names = []
            for cname, values, attrs in coords:
                if cname not in nc.dimensions:
                    nc.dimensions[cname] = len(values)
                    var = nc.create_variable(cname, (cname,), data=values)
                    for k, v in attrs.items():
                        var.attrs[k] = v
                elif nc.dimensions[cname].size != len(values):
                    refuse(
                        "subset_dims_conflict",
                        f"{name}: axis {cname} has {len(values)} values here and "
                        f"{nc.dimensions[cname].size} in another variable",
                    )
                dim_names.append(cname)
            data = read(dataset, sel, decode=True)
            var = nc.create_variable(name, tuple(dim_names), data=data, compression="gzip")
            for k, v in cf.attributes(dataset).items():
                if k in ("_FillValue", "missing_value", "scale_factor", "add_offset"):
                    continue
                var.attrs[k] = v
            var.attrs["source_variable"] = dataset.name
            var.attrs["source_selection"] = json.dumps(sel.as_dict())
            written.append({"name": name, "shape": list(data.shape), "dims": dim_names})
    return {"path": str(out), "format": "netcdf", "variables": written}


def _b64(array: np.ndarray) -> str:
    raw = np.ascontiguousarray(array).tobytes()
    return base64.b64encode(struct.pack("<Q", len(raw)) + raw).decode("ascii")


def _vtr(
    path: Path, x: np.ndarray, y: np.ndarray, z: np.ndarray, fields: dict[str, np.ndarray]
) -> None:
    nx, ny, nz = len(x), len(y), len(z)
    extent = f"0 {nx - 1} 0 {ny - 1} 0 {nz - 1}"

    def arr(n: str, a: np.ndarray, kind: str) -> str:
        return f'<DataArray type="{kind}" Name={quoteattr(n)} format="binary">{_b64(a)}</DataArray>'

    # VTK point order: x fastest, then y, then z -> a (z, y, x) array in C order.
    first = next(iter(fields))
    point_data = "".join(arr(n, v.astype("<f4"), "Float32") for n, v in fields.items())
    body = (
        '<?xml version="1.0"?>\n'
        '<VTKFile type="RectilinearGrid" version="1.0" byte_order="LittleEndian" '
        'header_type="UInt64">\n'
        f'<RectilinearGrid WholeExtent="{extent}"><Piece Extent="{extent}">\n'
        f"<PointData Scalars={quoteattr(first)}>{point_data}</PointData>\n"
        f"<Coordinates>{arr('x', x.astype('<f8'), 'Float64')}"
        f"{arr('y', y.astype('<f8'), 'Float64')}{arr('z', z.astype('<f8'), 'Float64')}"
        "</Coordinates>\n</Piece></RectilinearGrid></VTKFile>\n"
    )
    path.write_text(body, encoding="ascii")


def _same_grid(coords: list, other: list, name: str, first: str) -> None:
    for (axis, a, _), (_, b, _) in zip(coords, other, strict=True):
        if a.shape != b.shape or not np.allclose(np.asarray(a, "f8"), np.asarray(b, "f8")):
            refuse(
                "vtk_grids_differ",
                f"{name} and {first} differ along {axis}; one VTK series needs one grid "
                "(the same box and times in every variable)",
            )


def write_vtk_series(
    items: list[tuple[h5py.Dataset, Selection, str]],
    out: Path,
    vertical: dict[str, float] | None,
) -> dict[str, Any]:
    """Write ``(dataset, selection, name)`` items on one grid as ``.vtr`` files and a ``.pvd``.

    Every item is one point array in each step, so variables kept in separate files (ERA5
    stores one per file) are seen together: one isosurface of cloud liquid, one of ice.
    """
    dataset, sel, _ = items[0]
    coords = _coord_subset(dataset, sel)
    datas = {}
    for ds, s_, name in items:
        data = read(ds, s_, decode=True)
        if data.ndim not in (3, 4):
            refuse(
                "vtk_needs_3d",
                f"a 3D view needs 3 or 4 dims (time, z, y, x); {name} has {data.ndim}",
            )
        if datas:
            _same_grid(coords, _coord_subset(ds, s_), name, next(iter(datas)))
        datas[name] = data if data.ndim == 4 else data[None]
    if len(coords) == 3:
        coords = [("time", np.array([0.0]), {}), *coords]
        times: list[float] = [0.0]
        time_units = None
    else:
        times = [float(t) for t in coords[0][1]]
        time_units = coords[0][2].get("units")
    (_, zc, zattrs), (_, yc, _), (_, xc, _) = coords[1:]
    zc = zc.astype(np.float64)
    if vertical:
        ref, scale = float(vertical.get("reference", 1.0)), float(vertical.get("scale", 1.0))
        if np.any(zc <= 0) or ref <= 0:
            refuse("vertical_invalid", "a log vertical mapping needs positive coordinates")
        zc = scale * np.log(ref / zc)
    order = [np.argsort(zc), np.argsort(yc), np.argsort(xc)]
    zc, yc, xc = zc[order[0]], yc[order[1]].astype(np.float64), xc[order[2]].astype(np.float64)
    for name, data in datas.items():
        data = data[:, order[0]][:, :, order[1]][:, :, :, order[2]]
        datas[name] = np.where(np.isfinite(data), data, 0.0)
    out.mkdir(parents=True, exist_ok=True)
    stem = out.name
    entries = []
    for i, t in enumerate(times):
        piece = out / f"{stem}_{i:04d}.vtr"
        _vtr(piece, xc, yc, zc, {name: data[i] for name, data in datas.items()})
        entries.append(f'<DataSet timestep="{t:.6g}" part="0" file="{piece.name}"/>')
    index = out / f"{stem}.pvd"
    index.write_text(
        '<?xml version="1.0"?>\n<VTKFile type="Collection" version="1.0">\n<Collection>\n'
        + "\n".join(entries)
        + "\n</Collection>\n</VTKFile>\n",
        encoding="ascii",
    )
    meta = {
        "sources": [
            {"file": ds.file.filename, "variable": ds.name, "selection": s_.as_dict(), "name": n}
            for ds, s_, n in items
        ],
        "vertical": vertical or {},
        "vertical_units": zattrs.get("units"),
        "written": _now(),
    }
    (out / f"{stem}.provenance.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    fields = [
        {"name": name, "range": [float(np.nanmin(data)), float(np.nanmax(data))]}
        for name, data in datas.items()
    ]
    return {
        "path": str(index),
        "format": "vtk",
        "steps": len(times),
        "grid": [len(xc), len(yc), len(zc)],
        "bounds": [
            float(xc[0]),
            float(xc[-1]),
            float(yc[0]),
            float(yc[-1]),
            float(zc[0]),
            float(zc[-1]),
        ],
        "fields": fields,
        "field": fields[0]["name"],
        "range": fields[0]["range"],
        "times": times,
        "time_units": time_units,
        "times_iso": [cf.time_text(t, time_units) for t in times] if time_units else None,
    }
