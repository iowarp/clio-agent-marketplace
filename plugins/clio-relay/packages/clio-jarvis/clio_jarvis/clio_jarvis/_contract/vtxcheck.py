"""Open an ADIOS2 BP with ParaView's ADIOS2VTXReader and report what a view would see.

Usage: pvpython --force-offscreen-rendering vtxcheck.py <bp-dir> <array> [png]
Prints one JSON line: steps, time values, arrays, extent, last-step range.
"""

import json
import sys

from paraview import servermanager
from paraview.simple import (
    ADIOS2VTXReader,
    ColorBy,
    GetActiveViewOrCreate,
    GetAnimationScene,
    ResetCamera,
    SaveScreenshot,
    Show,
    Slice,
)

path, array = sys.argv[1], sys.argv[2]
png = sys.argv[3] if len(sys.argv) > 3 else None

reader = ADIOS2VTXReader(FileName=path)
reader.UpdatePipelineInformation()
times = list(reader.TimestepValues or [])
last = times[-1] if times else 0.0
reader.UpdatePipeline(last)
info = reader.GetDataInformation()
cell = [reader.CellData.GetArray(i).GetName() for i in range(reader.CellData.GetNumberOfArrays())]
point = [reader.PointData.GetArray(i).GetName() for i in range(reader.PointData.GetNumberOfArrays())]
assoc = reader.PointData if array in point else reader.CellData
value_range = list(assoc[array].GetRange()) if array in point + cell else None
first_range = None
if times:
    reader.UpdatePipeline(times[0])
    first_range = list(assoc[array].GetRange()) if array in point + cell else None
report = {
    "path": path,
    "steps": len(times),
    "times_head": times[:3],
    "times_tail": times[-3:],
    "point_arrays": point,
    "cell_arrays": cell,
    "bounds": list(info.GetBounds()),
    "points": info.GetNumberOfPoints(),
    "cells": info.GetNumberOfCells(),
    "array": array,
    "first_range": first_range,
    "last_range": value_range,
}
print("VTXCHECK " + json.dumps(report))

if png and times:
    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [800, 600]
    sl = Slice(Input=reader)
    sl.SliceType.Normal = [0.0, 0.0, 1.0]
    display = Show(sl, view)
    ColorBy(display, ("POINTS" if array in point else "CELLS", array))
    display.RescaleTransferFunctionToDataRange(True, False)
    scene = GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    scene.AnimationTime = last
    view.ViewTime = last
    ResetCamera(view)
    SaveScreenshot(png, view)
    print("VTXCHECK png " + png)
