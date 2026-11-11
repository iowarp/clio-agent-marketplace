---
name: acquire-earthscope-gnss
title: Acquire EarthScope GNSS Data
description: Use to find and stage EarthScope GNSS station catalogs and position time series from the National Data Platform, with stations picked on a map, for the geodesy skills.
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
station-metadata catalogs and per-station position time series. It adds
EarthScope's conventions to `work-with-ndp`, which explains the NDP tools,
organizations, datasets and resources; load it first if it is not loaded.
Raw observation files (RINEX) and EarthScope's own web services outside NDP
are not covered; say so when a request needs them. Which datasets and
resources exist, their names, columns and units change over time: discover
them every session and never carry them over from memory.

## What EarthScope publishes in NDP

- **Organization.** Resolve EarthScope's organization id with
  `connected_data_ndp_organizations` (query "earthscope") and pass it as
  `organization` to `connected_data_search_ndp`.
- **Per-station position series.** One dataset per station stream, titled
  `STATION.NETWORK.LOCATION.CHANNEL` (station code, network code, location
  code, channel). One station can have several streams. Each holds a CSV
  position series, a PNG preview and an HTML dashboard link: the CSV is the
  measurement; the preview and dashboard are not data. The series are
  high-rate (1 Hz) east/north/up displacements with one-sigma columns over a
  short window. Read the header, time representation, first and last epochs
  and value magnitudes from the staged file; the record does not state units
  or frame, so state what you inferred and why.
- **Station catalog.** A station-metadata table (one row per station with
  coordinates) is the way to choose stations by place. It may be published
  with no organization, so an organization-filtered search can miss it:
  search again without the filter ("earthscope station") before concluding
  it is absent.
- **Services and descriptions.** Records whose resource is a `service`
  (EarthScope's FDSN Station service, on-demand streams) or an HTML "public
  description" of a derived collection are not data files. Use a service
  only through an Endpoint when the user needs it.

## Discover

1. **Search** with `connected_data_search_ndp` using a few distinctive terms
   ("gnss", a station code, "station"), with and without the organization.
   Results carry dataset ids, titles, organizations and resources (id, name,
   format, size). Pages hold 50 datasets; follow `next_offset` or narrow the
   query. Retry a zero-match search with fewer terms before concluding
   something is absent.
2. **Classify each candidate** from its description and, once staged, a
   bounded look: a station catalog has one row per station with coordinates;
   a position series has epochs and components for one station stream. A
   file name or title is a hint, not evidence.
3. **Note the product facts** the geodesy skills need: frame, producer,
   units, cadence, time span and time representation, from the record or the
   file itself.

When the `ndp` MCP server is running, `run_code` scripts can also call
`tools.ndp.search_datasets` (field searches such as `owner_org` or
`resource_format`) and `tools.ndp.get_dataset_details` (resource URLs) to
filter many station records in one step. It is optional: everything here
works with the built-in tools.

## Stage

- **Local first.** If the active workspace already holds the resource (same
  name and size), use it and say so; otherwise stage it.
- Attach exactly the resources you need with
  `connected_data_connect(provider="ndp", root=<dataset id>, label=<title>,
  configuration={"endpoint_id": <endpoint_id>, "resource_ids": [<id>]})`,
  wait for the indexing task, then `connected_data_download` it (or
  `connected_data_open` to read it linked). Report the staged path and size.
  Position series are tens of megabytes; stage only the streams the analysis
  needs.
- A staged catalog is raw. Normalize it with `station-catalogs` before any
  spatial filter: headers can carry unit labels or repeat a name, and a
  column titled for one coordinate can hold another. Identify the id,
  latitude and longitude columns by value range and documentation.

## Choose stations

1. Resolve the place with `resolve-region`, then list the normalized
   catalog's stations within the radius (`station_catalog.py within`, or
   `geo_filter_points_by_radius` when the geo tools are available). A zero
   count is a result only when the filter succeeded on nonzero input rows
   with few invalid skips; otherwise the filter failed. Never widen the
   region to manufacture a candidate.
2. With several ranked stations, show them before staging any series: load
   the catalog skill `a2ui-catalog-earthscope-stations` and create the
   `earthscope-stations` surface (map and picker) from the tool-returned
   points only. Pause with `ask_user(..., surface_id="earthscope-stations")`
   when you continue in this turn once the user picks, or end the turn with the
   surface ready when choosing is the natural end. Stage a series only for
   stations the user selected, or the leading candidate when the user asked
   you to choose.
3. For each selected station, search NDP for its code within the
   organization and choose the series dataset whose title begins with that
   code; when it has several streams, say which one you used. Try the next
   ranked station only when a station has no series or staging fails. Never
   derive a station id or file name from a place name.

## Hand over

Record what was found in the workflow state: the region (`geospatial`), the
catalog and its normalized path (`catalog`, `station_catalog`), and the
series (`acquisition` with `local_path`; `analysis_ready` only for an on-disk
series, `metadata_only` when only the catalog was staged). Then analyse the
series with `gnss-time-series`, reading its columns, units and frame from the
file first. A window of days gives transient motion and noise, not a
long-term station velocity: say so rather than quoting a secular rate from
it. Copy every id, path and number from tool results.
