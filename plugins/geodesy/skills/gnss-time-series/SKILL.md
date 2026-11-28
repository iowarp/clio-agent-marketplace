---
name: gnss-time-series
title: GNSS Position Time Series
description: Use to analyse GNSS station position time series - components, reference frames, trajectory models, outliers, noise and rate uncertainty (bundles fit_trajectory.py).
keywords:
- level:L1
- geodesy
- gnss
- time-series
---

# GNSS position time series

## What a series is

A station's series gives its position at each epoch (usually one solution per
day), either as geocentric X, Y, Z, as latitude, longitude and height, or as
displacements east, north and up (E, N, U) from a reference position. Every
number depends on these, read from the file and its documentation:

- **components and units** (m or mm; headers may carry unit labels on a
  second row) and which columns hold per-epoch uncertainties;
- **the reference frame**: a global frame (an ITRF or IGS realization) or a
  plate-fixed frame. Rates differ between frames by the plate's motion, so
  stations compare only within one named frame;
- **the time representation** (decimal year, date, MJD) and the cadence, including gaps and repeated epochs;
- **the producer and processing** (analysis centre, solution type), because
  two products for one station need not agree.

E, N, U from X, Y, Z: rotate the difference from the reference position by
the reference latitude and longitude (E = -sin(lon) dX + cos(lon) dY;
N = -sin(lat) cos(lon) dX - sin(lat) sin(lon) dY + cos(lat) dZ;
U = cos(lat) cos(lon) dX + cos(lat) sin(lon) dY + sin(lat) dZ).

## The trajectory model

Each component is fitted with weighted least squares:
intercept + rate (t - t0) + offsets at known epochs + annual and semiannual
sine and cosine terms (+ postseismic logarithmic or exponential terms when a
large earthquake demands it, an extension worth naming).

- **Offsets** come from equipment changes (antenna, receiver, radome) in the
  station log and from earthquakes, and are estimated at those epochs. A jump
  with no known cause is a finding; absorbing it into the model hides it.
- **Seasonal terms** are usually largest in the vertical (hydrological and
  atmospheric loading), with an amplitude and phase per component.
- **Short spans** trade the annual term against the rate: with less than about
  2.5 years, rates can be biased by seasonal signal.
- **Outliers** lie beyond a robust threshold of normalized residuals; how
  many were removed is part of the fit.

## Uncertainty

GNSS noise is time-correlated (flicker and random-walk components), so the
white-noise formal sigma of a rate is a lower bound, often by a large factor;
the residual autocorrelation shows how far. Realistic uncertainties come from a
noise model (for example with Hector) or a robust estimator such as MIDAS
(median of slopes between samples one year apart). A rate from this fit and a
MIDAS-style rate that disagree beyond their uncertainties usually point to
unmodelled steps.

For several stations in a region, common-mode error (a signal shared by all)
can dominate residuals, and small regional differences can be that signal.

## The bundled script

`load_skill` reports this skill's directory as `SKILL_ROOT`:

```text
uv run --no-project "SKILL_ROOT/scripts/fit_trajectory.py" SERIES.csv --time TIME_COL \
    --components E=COL N=COL U=COL [--sigmas E=COL N=COL U=COL] [--offset EPOCH ...] \
    [--scale 1000 --units mm] [--no-seasonal] [--residuals RESIDUALS.csv] --out FIT.json
```

Columns are named by header or `#index`. Rows that do not parse (unit rows,
blanks) are skipped and counted. The JSON gives per component: rows used,
outliers, span, rate with formal and scaled sigma, offsets, annual and
semiannual amplitude and phase, WRMS, reduced chi-square, residual lag-1
autocorrelation, a MIDAS-style rate, and caveats, and is the analysis's
record in the workspace.

## Presenting

E, N and U against time with the model and the offset epochs marked, and the
residuals, read best as one line per component on a shared time axis, or one
panel per component when scales differ. `present-interactive-analysis` makes
an interactive chart from the staged file (with the component columns folded
into one `component`/`displacement` pair). Horizontal velocity is east and
north rates with their uncertainties; its magnitude and azimuth mean something
only with the frame named.
