---
name: weather-extremes
title: Weather Extremes
description: Define and find weather extremes in reanalysis and model output - percentile thresholds and heat waves against a stated climatology, atmospheric rivers and other features detected and tracked as blobs, and their statistics.
keywords:
- level:L1
- weather
- extremes
- heat-wave
- atmospheric-river
---

# Weather extremes

An extreme is defined by a choice: the variable, the baseline period, the
percentile or absolute threshold, the window around each calendar day, and
the minimum duration. Make each choice, say why, and report it with the
events. A different choice gives different events; when the person asks
for one, keep both and compare.

## Thresholds and heat waves

1. `era5_fetch` the series or field (ARCO ERA5, no key). Keep the request
   inside the size the tool states; split a long or wide request.
2. `threshold_events` with the baseline period, the percentile and its
   calendar-day window, and the minimum duration. It returns the
   climatology, the threshold and each event's start, end, peak and
   intensity.
3. Show the series against the climatology and threshold, with the events
   marked; the person may pick an event there.

## Features as blobs (atmospheric rivers, blocks, heat domes)

1. Compute the field the feature is defined on (for rivers, integrated
   vapour transport) and state the definition and threshold.
2. `detect_blobs` finds regions above the threshold per time,
   `stitch_blobs` links them in time, `blob_stats` gives size, duration and
   intensity per object.
3. Show the objects on the layered map with the time axis, and the table
   of objects; landfalling or long-lived ones are usually what matters.

## Cyclones

`tc_track` with its explicit backend (see `forecast-probabilities`).
