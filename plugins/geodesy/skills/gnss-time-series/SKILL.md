---
name: gnss-time-series
title: GNSS Position Time Series
description: Analyse GNSS station position time series from any network - east/north/up components, reference frames, trajectory models (rate, offsets, annual and semiannual terms), outliers, noise and rate uncertainty, and how to present them. Bundles fit_trajectory.py.
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
displacements east, north and up (E, N, U) from a reference position. Before
any number, establish from the file and its documentation:

- **components and units** (m or mm; headers may carry unit labels on a
  second row) and which columns hold per-epoch uncertainties;
- **the reference frame**: a global frame (an ITRF or IGS realization) or a
  plate-fixed frame. Rates differ between frames by the plate's motion;
  compare stations only within one frame and state it;
- **the time representation** (decimal year, date, MJD) and the cadence; look
  for gaps and repeated epochs;
- **the producer and processing** (analysis centre, solution type), because
  two products for one station need not agree.

E, N, U from X, Y, Z: rotate the difference from the reference position by
the reference latitude and longitude (E = -sin(lon) dX + cos(lon) dY;
N = -sin(lat) cos(lon) dX - sin(lat) sin(lon) dY + cos(lat) dZ;
U = cos(lat) cos(lon) dX + cos(lat) sin(lon) dY + sin(lat) dZ).

## The trajectory model

Fit each component with weighted least squares:
intercept + rate (t - t0) + offsets at known epochs + annual and semiannual
sine and cosine terms (+ postseismic logarithmic or exponential terms when a
large earthquake demands it, stated as an extension).

- **Offsets** come from equipment changes (antenna, receiver, radome) in the
  station log and from earthquakes; estimate them at those epochs. A jump with
  no known cause is a finding to report, not something to hide in the model.
- **Seasonal terms** are usually largest in the vertical (hydrological and
  atmospheric loading). Report amplitude and phase per component.
- **Short spans** trade the annual term against the rate: with less than about
  2.5 years, rates can be biased by seasonal signal. Say so.
- **Outliers**: remove beyond a robust threshold of normalized residuals and
  report how many.

## Uncertainty

GNSS noise is time-correlated (flicker and random-walk components), so the
white-noise formal sigma of a rate is a lower bound, often by a large factor.
Report it as such, give the residual autocorrelation, and for final
uncertainties estimate a noise model (for example with Hector) or use a
robust estimator such as MIDAS (median of slopes between samples one year
apart). When a rate from this fit and a MIDAS-style rate disagree beyond their
uncertainties, look for unmodelled steps.

For several stations in a region, common-mode error (a signal shared by all)
can dominate residuals; mention it before interpreting small regional
differences.

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
autocorrelation, a MIDAS-style rate, and caveats. Keep it with the analysis
in the workspace.

## Presenting

Show E, N and U against time with the model and the offset epochs marked, and
the residuals; one line per component on a shared time axis, or one panel per
component when scales differ. Load `present-interactive-analysis` for an
interactive chart from the staged file (fold the component columns into one
`component`/`displacement` pair). Report horizontal velocity as east and north
rates with their uncertainties, and its magnitude and azimuth only with the
frame named.
