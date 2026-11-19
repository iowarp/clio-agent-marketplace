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

## Choose what to fetch

- **Current-year or incident perimeters** change daily. Name the time you
  fetched them; a later fetch can differ.
- **Historical perimeter archives** hold one final perimeter per fire, usually
  with a year, a fire name and an agency id. Prefer them for history.
- Fetch by region with `fetch_features` and a `where` clause on the year or
  date field when the question is about a period. Describe the layer first to
  learn its field names; do not guess them.
- Check `paging.complete`. A truncated fire history undercounts.

## Pick the perimeter of record

One fire can appear several times: daily updates, versions from different
agencies, or both a current and an archived copy. Group by the fire's id (or its
name, year and start date) and keep one perimeter per fire, by a stated rule
(the final or latest perimeter, or the one flagged as of record). Report how
many duplicates were dropped.

## Areas and reburns

- **Burned area in a period:** dissolve the period's perimeters
  (`overlay_features` with `dissolve`), so land that burned twice counts once.
  Report the per-fire sum alongside it only if it is labelled as such.
- **Burned area by year:** dissolve within each year (`by` the year field).
- **Reburn and recurrence:** intersect years (`overlay_features` with
  `identity` or `intersection`) to count how many times each area burned, and
  map the count.
- **Inside a region:** clip to the region or its boundary polygon first
  (`clip_features`), so fires that only touch it are measured inside it.

## What perimeters do not say

A perimeter is the outer edge of a fire, not its severity. It contains unburned
islands, and its mapping method varies (infrared flights, satellite detection,
hand GPS). Severity needs burn-severity rasters (differenced spectral indices),
and fine-scale burned area needs those or imagery. Small fires below an
archive's size threshold are missing. State these limits next to any number.
