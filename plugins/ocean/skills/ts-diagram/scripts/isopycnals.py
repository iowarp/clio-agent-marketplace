# /// script
# requires-python = ">=3.10"
# dependencies = ["gsw>=3.6", "pandas>=2.2", "pyarrow>=17"]
# ///
"""Append isopycnal lines (sigma0, TEOS-10) to a cast table for a T-S diagram.

Reads a table with Absolute Salinity ``SA`` and Conservative Temperature ``CT``
(Parquet or CSV), adds rows with ``kind = "isopycnal"`` tracing constant sigma0
across the data's SA-CT range at a round interval, marks one point per line
with ``label = true`` for its value, and writes Parquet or CSV by the output
name. The cast rows are kept unchanged, with ``kind = "cast"``.

    uv run isopycnals.py casts.parquet casts_ts.parquet [--interval 0.5]
"""

from __future__ import annotations

import argparse
import math

import gsw
import numpy as np
import pandas as pd


def read(path: str) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


def isopycnals(table: pd.DataFrame, interval: float | None) -> pd.DataFrame:
    sa = table["SA"].to_numpy(dtype=float)
    ct = table["CT"].to_numpy(dtype=float)
    ok = np.isfinite(sa) & np.isfinite(ct)
    if not ok.any():
        raise SystemExit("no finite SA and CT values in the table")
    sa_lo, sa_hi = sa[ok].min(), sa[ok].max()
    ct_lo, ct_hi = ct[ok].min(), ct[ok].max()
    pad_sa = 0.05 * max(sa_hi - sa_lo, 0.1)
    pad_ct = 0.05 * max(ct_hi - ct_lo, 0.5)
    grid_sa = np.linspace(sa_lo - pad_sa, sa_hi + pad_sa, 120)
    grid_ct = np.linspace(ct_lo - pad_ct, ct_hi + pad_ct, 120)
    sigma = gsw.sigma0(*np.meshgrid(grid_sa, grid_ct))
    lo, hi = float(np.nanmin(sigma)), float(np.nanmax(sigma))
    if interval is None:
        raw = (hi - lo) / 8
        power = 10 ** math.floor(math.log10(raw))
        interval = min((s * power for s in (1, 2, 5, 10) if s * power >= raw), default=raw)
    rows = []
    for level in np.arange(math.ceil(lo / interval) * interval, hi, interval):
        # CT on this isopycnal at each SA: invert sigma0 along each grid column.
        points = []
        for j, s in enumerate(grid_sa):
            column = sigma[:, j]
            k = np.where(np.diff(np.sign(column - level)) != 0)[0]
            if k.size:
                i = int(k[0])
                f = (level - column[i]) / (column[i + 1] - column[i])
                points.append((s, grid_ct[i] + f * (grid_ct[i + 1] - grid_ct[i])))
        for n, (s, c) in enumerate(points):
            rows.append({"kind": "isopycnal", "SA": s, "CT": c, "sigma0": round(level, 4),
                         "label": n == len(points) - 1})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("table")
    parser.add_argument("output")
    parser.add_argument("--interval", type=float, default=None, help="sigma0 spacing, kg/m3")
    args = parser.parse_args()
    table = read(args.table).assign(kind="cast")
    lines = isopycnals(table, args.interval)
    out = pd.concat([table, lines], ignore_index=True)
    if args.output.endswith(".parquet"):
        out.to_parquet(args.output, index=False)
    else:
        out.to_csv(args.output, index=False)
    print(f"{len(table)} cast rows, {lines['sigma0'].nunique()} isopycnals "
          f"({len(lines)} rows) -> {args.output}")


if __name__ == "__main__":
    main()
