"""Write a frame of particles (atoms, beads) as a VTK XML PolyData file.

Molecular dynamics packages turn each trajectory frame into one ``.vtp``: the
positions as points with one vertex cell each, per-particle arrays as point
data, and the frame's time as the ``TimeValue`` field array, which ParaView's
XML readers report as the step's time. The file is written beside its final
name and renamed into place, so a reader that follows the folder never opens
half a frame. Pure Python (``array`` and ``base64``): the jarvis-cd runtime
needs no NumPy for it.
"""

from __future__ import annotations

import base64
import os
import struct
import sys
from array import array
from collections.abc import Mapping, Sequence
from pathlib import Path

_VTK_TYPES = {"f": "Float32", "d": "Float64", "i": "Int32", "q": "Int64"}


def _little(values: array) -> bytes:
    if sys.byteorder != "little":
        values = array(values.typecode, values)
        values.byteswap()
    return values.tobytes()


def _data_array(name: str | None, values: array, components: int) -> str:
    raw = _little(values)
    encoded = base64.b64encode(struct.pack("<I", len(raw)) + raw).decode("ascii")
    named = f' Name="{name}"' if name else ""
    return (
        f'<DataArray type="{_VTK_TYPES[values.typecode]}"{named} NumberOfComponents="{components}" '
        f'format="binary">{encoded}</DataArray>'
    )


def write_points_vtp(
    path: Path,
    positions: Sequence[float],
    point_arrays: Mapping[str, tuple[array, int]],
    time: float | None = None,
    field_arrays: Mapping[str, Sequence[float]] | None = None,
) -> None:
    """Write ``positions`` (x0 y0 z0 x1 ...) with ``point_arrays`` {name: (values, components)}."""
    count = len(positions) // 3
    fields = dict(field_arrays or {})
    if time is not None:
        fields["TimeValue"] = [float(time)]
    field_xml = "".join(_data_array(name, array("d", values), 1) for name, values in fields.items())
    point_xml = "".join(_data_array(name, values, components) for name, (values, components) in point_arrays.items())
    text = (
        '<?xml version="1.0"?>\n'
        '<VTKFile type="PolyData" version="1.0" byte_order="LittleEndian" header_type="UInt32">'
        "<PolyData>"
        + (f"<FieldData>{field_xml}</FieldData>" if field_xml else "")
        + f'<Piece NumberOfPoints="{count}" NumberOfVerts="{count}" NumberOfLines="0" '
        'NumberOfStrips="0" NumberOfPolys="0">'
        f"<PointData>{point_xml}</PointData>"
        f"<Points>{_data_array(None, array('f', positions), 3)}</Points>"
        "<Verts>"
        + _data_array("connectivity", array("i", range(count)), 1)
        + _data_array("offsets", array("i", range(1, count + 1)), 1)
        + "</Verts></Piece></PolyData></VTKFile>\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.part")
    partial.write_text(text, encoding="ascii")
    os.replace(partial, path)
