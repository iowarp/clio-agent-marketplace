---
name: fire-perimeters
title: Fire Perimeters and Fire History
description: Use for questions about where and when fires burned - perimeters of one fire, fire history of a region, burned area by year, how often places reburned, time since last fire. Covers choosing the perimeter of record, dissolving overlaps, and stating what perimeter data cannot say.
keywords:
- level:L1
- wildfire
---

# Fire perimeters and fire history

Perimeter collections mix sources, dates and versions. A sum of polygon areas is
rarely the burned area.

## What to fetch

- **Current-year or incident perimeters** change daily, so the fetch time dates the result; a later fetch can
  differ.
- **Historical perimeter archives** hold one final perimeter per fire, usually
  with a year, a fire name and an agency id, which suits history.
- `fetch_features` fetches by region, with a `where` clause on the year or
  date field for a period. The layer's description gives its field names;
  guessed names match nothing.
- `paging.complete` says whether the result is whole. A truncated fire history
  undercounts.

## The perimeter of record

One fire can appear several times: daily updates, versions from different
agencies, or both a current and an archived copy. Grouping by the fire's id (or
its name, year and start date) leaves one perimeter per fire by a stated rule
(the final or latest perimeter, or the one flagged as of record); the number of
duplicates dropped belongs with the result.

## Areas and reburns

- **Burned area in a period:** the period's perimeters dissolved
  (`overlay_features` with `dissolve`), so land that burned twice counts once.
  A per-fire sum is a different number and needs its own label.
- **Burned area by year:** a dissolve within each year (`by` the year field).
- **Reburn and recurrence:** years intersected (`overlay_features` with
  `identity` or `intersection`) count how many times each area burned, which
  maps well.
- **Inside a region:** a clip to the region or its boundary polygon
  (`clip_features`) before measuring keeps fires that only touch it measured
  inside it.

## What perimeters do not say

A perimeter is the outer edge of a fire, not its severity. It contains unburned
islands, and its mapping method varies (infrared flights, satellite detection,
hand GPS). Severity needs burn-severity rasters (differenced spectral indices),
and fine-scale burned area needs those or imagery. Small fires below an
archive's size threshold are missing. These limits qualify any number from
perimeters.
