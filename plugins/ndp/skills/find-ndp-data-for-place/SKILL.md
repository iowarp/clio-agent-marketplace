---
name: find-ndp-data-for-place
title: Find NDP Data for a Place and Topic
description: Use when a question names a place and a topic (snowpack at a ski area, fire and vegetation around a lake, land motion in a basin) and the data may come from several NDP organizations. Turns the place and topic into catalog searches, finds national and statewide layers by theme, checks each candidate's coverage from its record or its own service, treats zero results as a reason to rephrase, and runs one branch per organization.
keywords:
- level:L2
- ndp
- discovery
---

# Find NDP data for a place and topic

The NDP catalog has no working search by place or time, and organizations
describe location, time and format differently. Find data the way a scientist
would: search for the names and the themes, then check each candidate's
coverage directly.

## 1. Expand the place and the topic

- **Place:** run `resolve-region`. Keep its bounds for every check and its name
  list for searching: the place, the containing county, forest, watershed and
  state, the main features, the managing agencies.
- **Topic:** list the variables and their synonyms the way catalogs word them
  (snowpack, snow depth, snow water equivalent; canopy, fuels, land cover,
  vegetation type; fire perimeters, burn severity, fire history; subsidence,
  uplift, GNSS position). Add the measurement that would answer the question
  (lidar, DEM, station series, imagery).

## 2. Search, several ways

`connected_data_search_ndp` combines words with AND, so search short:

1. Each place name alone, and each with one topic word.
2. Each topic word or measurement alone, with no place: national and
   statewide layers cover the region without naming it.
3. Per organization: list publishers with `connected_data_ndp_organizations`,
   pick the ones whose holdings fit the topic, and search each with
   `organization` set and a theme word.

**Zero results is a reason to rephrase, not a finding.** Drop a word, use a
synonym, try the larger unit (county, state), try the theme without the place,
or the organization without the theme. Conclude that NDP lacks something only
after these variants, and list the queries you tried.

Record every query with its result count. Keep candidates in one table: title,
organization, catalog id, what it measures, resources and their kinds.

## 3. Check each candidate's coverage

Each search result carries `coverage`: the record's own `location` (a `bbox`
from whichever field it uses, with `span_degrees`) and `time` (start and end,
or only an issue date), with the source field named. Records that state
neither have `null`. Time can also appear only in the title or notes.

- A **world-wide or nation-wide box** (a large `span_degrees`) says nothing
  about the region. Treat it like a missing extent.
- **No usable extent:** ask the source. For a service resource (Esri REST,
  ArcGIS Feature Service, WFS, WCS, STAC), use the `get-geospatial-data` skill:
  `describe_geo_service` with the region's `bbox`, then a count query when it
  stays undetermined. For a multi-tile raster dataset, use
  `connected_data_ndp_tiles_covering`.
- **A blank `format` is missing metadata, not an unusable file.** Many records
  leave it empty for tiled rasters and point clouds; the search result then gives
  each resource's `name_suffix` (`.img`, `.tif`, `.laz`) and tallies the suffixes.
  Identify the file from that, and confirm with `describe_geo_service` on one
  resource, which reads raster and point-cloud headers. Set a candidate aside
  for its format only after a read has failed, and say which read.
- Classify each candidate as **overlaps**, **does not overlap** or **could not
  be determined (why)**, for both space and time. Keep all three groups in the
  answer.

## 4. One branch per organization

When candidates come from several organizations, give each organization its
own branch: a delegated task or workflow step when `delegation` is available,
otherwise one section of your own work at a time. Each branch:

- acquires through the right path: `connected_data_connect` with only the
  covering resources (or tiles) for files; the `get-geospatial-data` tools for
  services; the organization's own plugin when one is installed;
- returns a table with its source, region, period, what was fetched, and
  caveats (completeness, units, failed links and the alternative used).

Then merge with `harmonize-layers`. Its coverage report says what overlaps,
what does not, and what could not be determined.

## When links fail

A hub download that returns an HTTP error, or a resource whose `format` is
blank, is a local access problem, not missing data. Try the record's other
resources: the REST service behind a hub link, the VRT behind a folder of tiles,
the point-cloud source behind a viewer link. Report the failure and the path
that worked. A permission refusal from CLIO is a decision to report or ask
about, not proof that the data is closed.
