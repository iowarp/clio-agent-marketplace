---
name: acquire-earthscope-gnss
title: Acquire EarthScope GNSS Data
description: Find EarthScope GNSS station catalogs and per-station position time series in the National Data Platform, stage them with the ndp tools, let the user pick stations on a map, and hand a normalized catalog and a staged series to the geodesy skills - discovering resources, columns and units instead of assuming them.
keywords:
- level:L2
- earthscope
- gnss
- ndp
---

# Acquire EarthScope GNSS data

## Contract

This skill covers GNSS data from EarthScope (the consortium formed from
UNAVCO and IRIS) as the National Data Platform (NDP) catalog publishes it:
station-metadata catalogs and per-station position time series. Raw
observation files (RINEX) and EarthScope's own web services outside NDP are
not covered; say so when a request needs them. Which datasets and resources
exist, their names, columns and units change over time: discover them every
session and never carry them over from memory.

## Discover

1. **Search** with `ndp_search_datasets` using a few distinctive terms (a
   publisher, "gnss", "station"); `ndp_list_organizations` finds the
   publisher's id for `owner_org`. A search hit is compact: title, id,
   resource count and formats, not resource URLs. Retry a zero-match search
   with fewer terms before concluding something is absent.
2. **Read the record** with `ndp_get_dataset_details` for its resources:
   name, URL, format, size and description.
3. **Classify each candidate** from its description and, once staged, a
   bounded look: a station catalog has one row per station with coordinates;
   a position time series has epochs and components for one station. A file
   name or title is a hint, not evidence.
4. **Note the product facts** the geodesy skills need: reference frame,
   producer or solution, units, cadence and time representation, from the
   resource description or the file's own header.

Keep the exact resource URL in the session state and reuse it; repeat the
bounded search only when it is no longer available.

## Stage

- **Local first.** If the active workspace already holds a file with the
  resource's name and the same size, use it and say so; otherwise stage it.
- `ndp_stage_resource(url, output_dir=<workspace>)` downloads up to a size cap
  (50 MiB unless `max_bytes` is given). Raise `max_bytes` from the resource's
  advertised size only for a file the user needs, and report the staged
  path and size.
- A staged catalog is raw. Normalize it with `station-catalogs` before any
  spatial filter: headers can carry unit labels or repeat a name, and a
  column titled for one coordinate can hold another. Identify the id,
  latitude and longitude columns by value range and documentation.

## Choose stations

1. Resolve the place with `resolve-region` and filter the normalized catalog
   with `geo_filter_points_by_radius` (explicit `id`, `latitude`, `longitude`
   columns). A zero count is a result only when the filter succeeded on
   nonzero input rows with few invalid skips; otherwise the filter failed.
   Never widen the region to manufacture a candidate.
2. With several ranked stations, show them before staging any series: load
   the catalog skill `a2ui-catalog-earthscope-stations` and create the
   `earthscope-stations` surface (map and picker) from the tool-returned
   points only. Pause with `ask_user(..., surface_id="earthscope-stations")`
   when you continue in this turn once the user picks, or end the turn with the
   surface ready when choosing is the natural end. Stage a series only for
   stations the user selected, or the leading candidate when the user asked
   you to choose.
3. For each selected station, search NDP for its id, choose the resource that
   the record identifies as that station's position series, and stage it. Try
   the next ranked station only when a station has no such resource or
   staging fails. Never derive a station id or file name from a place name.

## Hand over

Record what was found in the workflow state: the region (`geospatial`), the
catalog and its normalized path (`catalog`, `station_catalog`), and the
series (`acquisition` with `local_path`; `analysis_ready` only for an on-disk
series, `metadata_only` when only the catalog was staged). Then analyse the
series with `gnss-time-series`, reading its columns, units and frame from the
file first. Copy every id, URL, path and number from tool results.
