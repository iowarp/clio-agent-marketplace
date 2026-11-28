---
name: acquire-earthscope-gnss
title: Acquire EarthScope GNSS Data
description: Use when finding and staging EarthScope GNSS station catalogs and position time series from the National Data Platform, with stations picked on a map, for the geodesy skills.
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
organizations, datasets and resources. Raw observation files (RINEX) and
EarthScope's own web services outside NDP are not covered. Which datasets and
resources exist, their names, columns and units change over time, so names
remembered from an earlier session are often stale.

## What EarthScope publishes in NDP

- **Organization.** `connected_data_ndp_organizations` (query "earthscope")
  resolves EarthScope's organization id, which `connected_data_search_ndp`
  takes as `organization`.
- **Per-station position series.** One dataset per station stream, titled
  `STATION.NETWORK.LOCATION.CHANNEL` (station code, network code, location
  code, channel). One station can have several streams. Each holds a CSV
  position series, a PNG preview and an HTML dashboard link: the CSV is the
  measurement; the preview and dashboard are not data. The series are
  high-rate (1 Hz) east/north/up displacements with one-sigma columns over a
  short window. The header, time representation, first and last epochs and
  value magnitudes are in the staged file; the record does not state units
  or frame, so they are inferences, and the reasoning behind them matters.
- **Station catalog.** A station-metadata table (one row per station with
  coordinates) is the way to choose stations by place. It may be published
  with no organization, so an organization-filtered search can miss it while a
  search without the filter ("earthscope station") finds it.
- **Services and descriptions.** Records whose resource is a `service`
  (EarthScope's FDSN Station service, on-demand streams) or an HTML "public
  description" of a derived collection are not data files. A service is reached
  only through an Endpoint.

## Discovery

- **Search.** `connected_data_search_ndp` with a few distinctive terms
  ("gnss", a station code, "station"), with and without the organization,
  returns dataset ids, titles, organizations and resources (id, name,
  format, size). Pages hold 50 datasets; `next_offset` continues, or a
  narrower query shortens the list. A zero-match search with many terms often
  matches with fewer.
- **Classifying a candidate.** Its description and, once staged, a bounded look
  tell the kinds apart: a station catalog has one row per station with
  coordinates; a position series has epochs and components for one station
  stream. A file name or title is a hint, not evidence.
- **Product facts.** The geodesy skills need the frame, producer, units,
  cadence, time span and time representation, from the record or the file
  itself.

`organization` and `resource_format` (for example CSV) narrow many station
records in one search, and each resource's own `description` comes with
`connected_data_search_ndp`.

## Staging

- **Local copies.** A resource the active workspace already holds (same name
  and size) needs no new staging.
- `connected_data_connect(provider="ndp", root=<dataset id>, label=<title>,
  configuration={"endpoint_id": <endpoint_id>, "resource_ids": [<id>]})`
  attaches chosen resources; after its indexing task, `connected_data_download`
  stages it (or `connected_data_open` reads it linked), with the staged path
  and size. Position series are tens of megabytes each, so staging only the
  streams the analysis needs keeps it small.
- A staged catalog is raw. `station-catalogs` normalizes it, and spatial filters
  depend on that: headers can carry unit labels or repeat a name, and a column
  titled for one coordinate can hold another. The id, latitude and longitude
  columns are identified by value range and documentation.

## Choosing stations

- **By place.** `resolve-region` fixes the place; `station_catalog.py within`,
  or `geo_filter_points_by_radius` when the geo tools are available, lists the
  normalized catalog's stations within the radius. A zero count is a result
  only when the filter succeeded on nonzero input rows with few invalid skips;
  otherwise the filter failed. A region widened until a candidate appears no
  longer answers the question asked.
- **Picking.** With several ranked stations, the catalog skill
  `a2ui-catalog-earthscope-stations` builds the `earthscope-stations` surface
  (map and picker) from the tool-returned points, so the person can pick before
  any series is staged. `ask_user(..., surface_id="earthscope-stations")` pauses
  for the pick when more work follows in this turn; ending the turn with the
  surface ready suits a request whose natural end is the choice. The series to
  stage are those of the selected stations, or the leading candidate when the
  person asked for a choice to be made.
- **Series per station.** An NDP search for the station code within the
  organization finds the series dataset whose title begins with that code; a
  station with several streams has several, and which one was used matters. The
  next ranked station is the fallback when a station has no series or staging
  fails. A station id or file name derived from a place name is a guess, not a
  catalog entry.

## Hand-over

The workflow state holds what was found: the region (`geospatial`), the
catalog and its normalized path (`catalog`, `station_catalog`), and the
series (`acquisition` with `local_path`; `analysis_ready` only for an on-disk
series, `metadata_only` when only the catalog was staged). `gnss-time-series`
analyses the series from its columns, units and frame as read from the file. A
window of days gives transient motion and noise, not a long-term station
velocity, so it does not support a secular rate. Ids, paths and numbers come
from tool results.