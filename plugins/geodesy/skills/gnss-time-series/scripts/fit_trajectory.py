# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24"]
# ///
"""Fit a GNSS station trajectory model to east/north/up (or any) components.

Model per component, by weighted least squares::

    x(t) = a + v (t - t0) + sum_k o_k H(t - t_k)
           + c1 cos 2pi(t - t0) + s1 sin 2pi(t - t0)      (annual)
           + c2 cos 4pi(t - t0) + s2 sin 4pi(t - t0)      (semiannual)

with offsets ``o_k`` only at the epochs you pass (equipment changes and
earthquakes from the station's logs or documentation). Outliers are removed
iteratively beyond ``--outlier`` robust standard deviations of the normalized
residuals, and counted. Alongside the fit, a simplified MIDAS-style rate (the
median of slopes between samples about one year apart that do not straddle a
given offset; Blewitt et al., 2016) gives a cross-check that resists seasonal
signals and undetected steps.

Formal uncertainties assume white noise. GNSS noise is time-correlated, so
they are lower bounds for the rate; the report also gives the lag-1
autocorrelation of the residuals and a scaled sigma, and says so.

    uv run --no-project fit_trajectory.py SERIES.csv --time COL --components E=COL N=COL U=COL \
        [--sigmas E=COL N=COL U=COL] [--offset EPOCH ...] [--scale 1000 --units mm] \
        [--no-seasonal] [--residuals OUT.csv] [--out FIT.json]

``--time`` values may be decimal years, ISO dates or date-times, or Modified
Julian Dates (``--time-format mjd``). Rows whose time or value does not parse
(repeated header rows, unit labels, blanks) are skipped and counted. The input
is only read.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def decimal_year(moment: datetime) -> float:
    start = datetime(moment.year, 1, 1, tzinfo=moment.tzinfo)
    end = datetime(moment.year + 1, 1, 1, tzinfo=moment.tzinfo)
    return moment.year + (moment - start).total_seconds() / (end - start).total_seconds()


def parse_time(text: str, fmt: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    if fmt in ("auto", "decimal-year", "mjd"):
        try:
            value = float(text)
        except ValueError:
            value = None
        if value is not None and math.isfinite(value):
            if fmt == "mjd" or (fmt == "auto" and value > 3000):
                return 2000.0 + (value - 51544.5) / 365.25
            return value
        if fmt != "auto":
            return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return decimal_year(moment)


def parse_pairs(items: list[str] | None) -> dict[str, str]:
    pairs = {}
    for item in items or ():
        label, sep, column = item.partition("=")
        if not sep:
            raise SystemExit(f"{item!r}: use LABEL=COLUMN")
        pairs[label] = column
    return pairs


def load(args: argparse.Namespace) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray], int]:
    path = Path(args.series)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    rows = list(csv.reader(lines, delimiter=delimiter))
    header = [h.strip() for h in rows[0]]

    def col(name: str) -> int:
        if name.startswith("#") and name[1:].isdigit():
            return int(name[1:])
        hits = [i for i, h in enumerate(header) if h == name]
        if len(hits) != 1:
            raise SystemExit(f"column {name!r}: {len(hits)} matches in {header}; use #index")
        return hits[0]

    components = parse_pairs(args.components)
    sigmas = parse_pairs(args.sigmas)
    t_i = col(args.time)
    c_i = {k: col(v) for k, v in components.items()}
    s_i = {k: col(v) for k, v in sigmas.items()}
    times, values, errors = [], {k: [] for k in c_i}, {k: [] for k in s_i}
    skipped = 0
    for row in rows[1:]:
        try:
            t = parse_time(row[t_i], args.time_format)
            vals = {k: float(row[i]) for k, i in c_i.items()}
            errs = {k: float(row[i]) for k, i in s_i.items()}
        except (ValueError, IndexError):
            skipped += 1
            continue
        if t is None or not all(map(math.isfinite, [*vals.values(), *errs.values()])):
            skipped += 1
            continue
        times.append(t)
        for k, v in vals.items():
            values[k].append(v * args.scale)
        for k, v in errs.items():
            errors[k].append(v * args.scale)
    if len(times) < 4:
        raise SystemExit(f"only {len(times)} usable rows")
    order = np.argsort(times)
    t = np.asarray(times)[order]
    return (
        t,
        {k: np.asarray(v)[order] for k, v in values.items()},
        {k: np.asarray(v)[order] for k, v in errors.items()},
        skipped,
    )


def design(t: np.ndarray, t0: float, offsets: list[float], seasonal: bool) -> tuple[np.ndarray, list[str]]:
    columns = [np.ones_like(t), t - t0]
    names = ["intercept", "rate"]
    for epoch in offsets:
        columns.append((t >= epoch).astype(float))
        names.append(f"offset@{epoch:.4f}")
    if seasonal:
        phase = 2 * np.pi * (t - t0)
        columns += [np.cos(phase), np.sin(phase), np.cos(2 * phase), np.sin(2 * phase)]
        names += ["annual_cos", "annual_sin", "semiannual_cos", "semiannual_sin"]
    return np.column_stack(columns), names


def fit_component(
    t: np.ndarray, x: np.ndarray, sigma: np.ndarray | None, offsets: list[float], seasonal: bool, k: float
) -> dict[str, Any]:
    t0 = float(np.round(np.mean(t), 4))
    sigma = sigma if sigma is not None else np.ones_like(x)
    keep = np.ones(len(t), bool)
    for _ in range(10):
        a, names = design(t[keep], t0, [e for e in offsets if t[keep].min() < e <= t[keep].max()], seasonal)
        w = 1.0 / sigma[keep]
        coef, *_ = np.linalg.lstsq(a * w[:, None], x[keep] * w, rcond=None)
        full, _ = design(t, t0, [e for e in offsets if t[keep].min() < e <= t[keep].max()], seasonal)
        normalized = (x - full @ coef) / sigma
        scale = 1.4826 * np.median(np.abs(normalized[keep] - np.median(normalized[keep])))
        new_keep = np.abs(normalized - np.median(normalized[keep])) <= k * max(scale, 1e-12)
        if np.array_equal(new_keep, keep):
            break
        keep = new_keep
    a, names = design(t[keep], t0, [e for e in offsets if t[keep].min() < e <= t[keep].max()], seasonal)
    w = 1.0 / sigma[keep]
    aw = a * w[:, None]
    coef, *_ = np.linalg.lstsq(aw, x[keep] * w, rcond=None)
    residual = x[keep] - a @ coef
    dof = max(int(keep.sum()) - len(coef), 1)
    chi2 = float(np.sum((residual * w) ** 2) / dof)
    cov = np.linalg.pinv(aw.T @ aw)
    formal = np.sqrt(np.diag(cov))
    scaled = formal * math.sqrt(chi2)
    params = {n: {"value": float(c), "formal_sigma": float(f), "scaled_sigma": float(s)} for n, c, f, s in zip(names, coef, formal, scaled)}
    out: dict[str, Any] = {
        "n_used": int(keep.sum()),
        "n_outliers": int((~keep).sum()),
        "span_years": float(t[keep].max() - t[keep].min()),
        "t0": t0,
        "rate_per_year": params["rate"],
        "offsets": {n.split("@", 1)[1]: params[n] for n in names if n.startswith("offset@")},
        "wrms": float(math.sqrt(np.sum((residual * w) ** 2) / np.sum(w**2))),
        "reduced_chi2": chi2,
        "residual_lag1_autocorrelation": float(np.corrcoef(residual[:-1], residual[1:])[0, 1]) if len(residual) > 2 else None,
    }
    if seasonal:
        for label, (c, s) in {"annual": ("annual_cos", "annual_sin"), "semiannual": ("semiannual_cos", "semiannual_sin")}.items():
            cv, sv = params[c]["value"], params[s]["value"]
            amp = math.hypot(cv, sv)
            amp_sigma = math.hypot(cv * params[c]["scaled_sigma"], sv * params[s]["scaled_sigma"]) / amp if amp else None
            out[label] = {"amplitude": amp, "amplitude_scaled_sigma": amp_sigma, "phase_rad": math.atan2(sv, cv)}
    out["midas_like_rate_per_year"] = midas_like(t[keep], x[keep], offsets)
    out["_keep"] = keep
    out["_model"] = (t0, coef, [e for e in offsets if t[keep].min() < e <= t[keep].max()])
    return out


def midas_like(t: np.ndarray, x: np.ndarray, offsets: list[float]) -> dict[str, Any] | None:
    """Median of slopes between samples about one year apart, not straddling an offset."""

    if t.max() - t.min() < 1.0:
        return None
    slopes = []
    j = 0
    for i in range(len(t)):
        target = t[i] + 1.0
        while j < len(t) - 1 and t[j] < target:
            j += 1
        best = min((j - 1, j), key=lambda n: abs(t[n] - target) if 0 <= n < len(t) else 9)
        if best <= i or abs(t[best] - target) > 0.01:
            continue
        if any(t[i] < e <= t[best] for e in offsets):
            continue
        slopes.append((x[best] - x[i]) / (t[best] - t[i]))
    if len(slopes) < 10:
        return None
    s = np.asarray(slopes)
    median = float(np.median(s))
    mad = 1.4826 * float(np.median(np.abs(s - median)))
    return {"value": median, "sigma": mad / math.sqrt(len(s) / 4), "pairs": len(s)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("series")
    parser.add_argument("--time", required=True)
    parser.add_argument("--time-format", choices=["auto", "decimal-year", "mjd", "iso"], default="auto")
    parser.add_argument("--components", nargs="+", required=True, metavar="LABEL=COLUMN")
    parser.add_argument("--sigmas", nargs="+", metavar="LABEL=COLUMN")
    parser.add_argument("--offset", nargs="*", default=[], help="offset epochs (decimal year or ISO date)")
    parser.add_argument("--no-seasonal", action="store_true")
    parser.add_argument("--outlier", type=float, default=5.0, help="robust sigmas for outlier removal")
    parser.add_argument("--scale", type=float, default=1.0, help="multiply values (e.g. 1000 for m to mm)")
    parser.add_argument("--units", default="as given")
    parser.add_argument("--residuals")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    offsets = []
    for item in args.offset:
        epoch = parse_time(item, "auto")
        if epoch is None:
            raise SystemExit(f"offset {item!r} is not a time")
        offsets.append(epoch)
    t, values, errors, skipped = load(args)
    fits = {
        label: fit_component(t, x, errors.get(label), sorted(offsets), not args.no_seasonal, args.outlier)
        for label, x in values.items()
    }
    caveats = [
        "Formal and scaled sigmas assume white noise; GNSS residuals are usually time-correlated "
        "(see residual_lag1_autocorrelation), so rate uncertainties are lower bounds. Estimate a "
        "noise model (for example with Hector) before quoting rate uncertainty as final.",
    ]
    span = float(t.max() - t.min())
    if span < 2.5 and not args.no_seasonal:
        caveats.append(
            "The span is under 2.5 years: annual terms and the rate trade off, so the rate can be "
            "biased by unmodelled seasonal signal (Blewitt and Lavallee, 2002)."
        )
    if not offsets:
        caveats.append("No offset epochs were given; check equipment logs and earthquakes for steps.")
    if args.residuals:
        with open(args.residuals, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time", "component", "value", "model", "residual", "used"])
            for label, fit in fits.items():
                t0, coef, used_offsets = fit["_model"]
                a, _ = design(t, t0, used_offsets, not args.no_seasonal)
                model = a @ coef
                for ti, xi, mi, ki in zip(t, values[label], model, fit["_keep"]):
                    writer.writerow([f"{ti:.6f}", label, xi, mi, xi - mi, bool(ki)])
    for fit in fits.values():
        fit.pop("_keep")
        fit.pop("_model")
    report = {
        "series": str(Path(args.series)),
        "units": args.units,
        "scale_applied": args.scale,
        "rows_used": int(len(t)),
        "rows_skipped_unparsable": skipped,
        "time_range": [float(t.min()), float(t.max())],
        "offset_epochs": sorted(offsets),
        "components": fits,
        "caveats": caveats,
    }
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
