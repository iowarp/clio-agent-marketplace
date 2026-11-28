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
the minimum duration. The events mean what those choices make them mean, so the
choices and their reasons belong with the events. A different choice gives
different events; when the person asks for one, both sets can be compared.

## Thresholds and heat waves

- `era5_fetch` gets the series or field (ARCO ERA5, no key). It states a size
  limit per request; a long or wide request fits as several.
- `threshold_events` takes the baseline period, the percentile and its
  calendar-day window, and the minimum duration. It returns the climatology,
  the threshold and each event's start, end, peak and intensity.
- The series against the climatology and threshold, with the events marked,
  is where the person may pick an event.

## Features as blobs (atmospheric rivers, blocks, heat domes)

The domain is set by the feature, not by the region the person named. A
feature that affects a region often sits upstream or poleward of it (a block
that shapes a European winter can be centred over Greenland or the eastern
Atlantic), and an index needs every latitude it references inside the data.
A box that holds the whole feature and its index is what can show what reaches
the region asked about.

- The feature is defined on a field (for rivers, integrated vapour transport)
  with a stated definition and threshold.
- `detect_blobs` finds regions above the threshold per time,
  `stitch_blobs` links them in time, `blob_stats` gives size, duration and
  intensity per object.
- The objects fit the layered map with the time axis, beside the table of
  objects; landfalling or long-lived ones are usually what matters.
  Landfall needs the coast on the same grid: ERA5 carries it as
  the variable land_sea_mask (one hour through `era5_fetch` is enough).

## Checking an event list

An event list is a finding, and the detection choices shape it. An independent
record of the same period (a published catalogue of the same kind of event, a
paper on that season, station totals, an agency's season summary) shows where
the events agree and where they differ, and why; a notable event of that record
missing from the list usually points at the domain or the definition.

## Cyclones

`tc_track` with its explicit backend (see `forecast-probabilities`).