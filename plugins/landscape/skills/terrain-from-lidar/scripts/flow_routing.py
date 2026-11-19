#!/usr/bin/env python3
"""D8 flow routing on a DEM: fill, flow direction, accumulation and streams.

Priority-flood with an epsilon gradient (Barnes, Lehman and Mulla, 2014) fills
depressions so every cell drains to the grid edge or a nodata cell; flats get a
tiny slope toward their outlet. D8 sends each cell's flow to its steepest
downslope neighbour. Accumulation counts upstream cells, reported as
contributing area. Streams are cells whose contributing area is at least a
threshold.

Usage:
    python flow_routing.py DEM.tif --out-prefix OUT [--stream-area-km2 0.5]

Writes OUT_accumulation.tif (contributing area in km^2), OUT_streams.tif
(1 = stream) and OUT_summary.json, and prints the summary. Needs numpy and
rasterio. The DEM must be in a projected CRS with metre units.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
from pathlib import Path

import numpy as np

MAX_CELLS = 25_000_000
OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def fill(dem: np.ndarray, valid: np.ndarray, epsilon: float = 1e-4) -> tuple[np.ndarray, int]:
    """Priority-flood fill; returns the filled DEM and how many cells were raised."""
    rows, cols = dem.shape
    filled = dem.astype("float64").copy()
    done = ~valid.copy()
    heap: list[tuple[float, int, int]] = []
    for r in range(rows):
        for c in range(cols):
            if not valid[r, c]:
                continue
            edge = r in (0, rows - 1) or c in (0, cols - 1)
            if not edge:
                edge = any(not valid[r + dr, c + dc] for dr, dc in OFFSETS)
            if edge:
                heapq.heappush(heap, (filled[r, c], r, c))
                done[r, c] = True
    raised = 0
    while heap:
        z, r, c = heapq.heappop(heap)
        for dr, dc in OFFSETS:
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols and not done[rr, cc]:
                done[rr, cc] = True
                if filled[rr, cc] <= z:
                    filled[rr, cc] = z + epsilon
                    raised += 1
                heapq.heappush(heap, (filled[rr, cc], rr, cc))
    return filled, raised


def direction(filled: np.ndarray, valid: np.ndarray, cell: float) -> np.ndarray:
    """Index into OFFSETS of each cell's steepest downslope neighbour; -1 for outlets."""
    rows, cols = filled.shape
    best = np.full(filled.shape, -1, dtype=np.int8)
    slope = np.zeros(filled.shape)
    padded = np.pad(filled, 1, constant_values=np.inf)
    vpad = np.pad(valid, 1, constant_values=False)
    for k, (dr, dc) in enumerate(OFFSETS):
        neighbour = padded[1 + dr : 1 + dr + rows, 1 + dc : 1 + dc + cols]
        nvalid = vpad[1 + dr : 1 + dr + rows, 1 + dc : 1 + dc + cols]
        drop = (filled - neighbour) / (cell * math.hypot(dr, dc))
        better = valid & nvalid & (drop > slope)
        best[better] = k
        slope[better] = drop[better]
    return best


def accumulate(filled: np.ndarray, valid: np.ndarray, flow: np.ndarray) -> np.ndarray:
    """Upstream cell counts, including the cell itself, processed from high to low."""
    rows, cols = filled.shape
    acc = np.where(valid, 1.0, 0.0)
    order = np.argsort(np.where(valid, filled, -np.inf), axis=None)[::-1]
    for flat in order:
        r, c = divmod(int(flat), cols)
        k = flow[r, c]
        if not valid[r, c] or k < 0:
            continue
        dr, dc = OFFSETS[k]
        acc[r + dr, c + dc] += acc[r, c]
    return acc


def route(dem: np.ndarray, valid: np.ndarray, cell: float, stream_area_km2: float) -> dict:
    filled, raised = fill(dem, valid)
    flow = direction(filled, valid, cell)
    acc = accumulate(filled, valid, flow)
    area_km2 = acc * cell * cell / 1e6
    streams = valid & (area_km2 >= stream_area_km2)
    return {
        "area_km2": area_km2,
        "streams": streams,
        "summary": {
            "cell_size_m": cell,
            "valid_cells": int(valid.sum()),
            "filled_cells": raised,
            "outlet_cells": int((valid & (flow < 0)).sum()),
            "stream_area_threshold_km2": stream_area_km2,
            "stream_cells": int(streams.sum()),
            "largest_contributing_area_km2": round(float(area_km2.max()), 4),
        },
    }


def main() -> None:
    import rasterio

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dem")
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--stream-area-km2", type=float, default=0.5)
    args = parser.parse_args()
    with rasterio.open(args.dem) as src:
        if src.crs is None or not src.crs.is_projected:
            raise SystemExit("The DEM must be in a projected CRS in metres; reproject it first.")
        if abs(abs(src.res[0]) - abs(src.res[1])) > 1e-6 * abs(src.res[0]):
            raise SystemExit("D8 needs square cells; resample the DEM to square cells first.")
        if src.width * src.height > MAX_CELLS:
            raise SystemExit(
                f"{src.width * src.height} cells exceed {MAX_CELLS}; read a smaller region "
                "or a coarser window first."
            )
        dem = src.read(1, masked=True)
        profile = src.profile
        cell = abs(src.res[0])
    valid = ~np.ma.getmaskarray(dem) & np.isfinite(dem.filled(np.nan))
    result = route(dem.filled(0).astype("float64"), valid, cell, args.stream_area_km2)
    profile.update(count=1, compress="deflate")
    out = Path(args.out_prefix)
    with rasterio.open(f"{out}_accumulation.tif", "w", **{**profile, "dtype": "float32",
                                                           "nodata": -1.0}) as dst:
        dst.write(np.where(valid, result["area_km2"], -1).astype("float32"), 1)
    with rasterio.open(f"{out}_streams.tif", "w", **{**profile, "dtype": "uint8", "nodata": 255}) as dst:
        dst.write(np.where(valid, result["streams"], 255).astype("uint8"), 1)
    summary = {**result["summary"], "outputs": [f"{out}_accumulation.tif", f"{out}_streams.tif"]}
    Path(f"{out}_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
