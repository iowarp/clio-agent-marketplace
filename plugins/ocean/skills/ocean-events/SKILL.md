---
name: ocean-events
title: Ocean Events
description: Find and characterise marine heatwaves against a stated climatology, bloom onsets, mixed-layer heat budgets over an event, and plan cruise stations along a forecast feature.
keywords:
- level:L1
- ocean
- marine-heatwave
- bloom
---

# Ocean events

## Marine heatwaves

The definition is a choice: the baseline period, the percentile, the window
around each day of year, the minimum duration and the gap that joins events.
Use a standard one (Hobday et al.) unless the person asks otherwise, state
it, and keep the person's alternative alongside when they change it.

- At a point: `mhw_point` gives events with duration, intensity and
  category.
- Over a region: `mhw_track` identifies and tracks events in a gridded
  sea surface temperature (a separate process; marEx, AGPL-3.0), and
  `mhw_events` gives each tracked event's metrics. Show them on the map
  with the time axis and as a table; the person may choose the event to
  study.

## Blooms

`bloom_phenology` gives the bloom start per year by a stated method
(threshold above the median, or cumulative). Report the method and the gaps
in the record.

## Mixed-layer heat budget

`mixed_layer_budget` over an event: surface flux, mixed layer depth and the
residual (advection and entrainment together). Say the products used for
each term; the residual carries every product's error.

## Cruise plans

`cruise_plan` places stations along a forecast feature within range of a
port, with steaming time. The person changes the stations on the map
(points layer, `editable`); read the edits back and replan.
