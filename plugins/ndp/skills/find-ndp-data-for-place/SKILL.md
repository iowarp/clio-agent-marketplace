---
name: find-ndp-data-for-place
title: Find NDP Data for a Place and Topic
description: Use when a question names a place and a topic (snowpack at a ski area, fire and vegetation around a lake, land motion in a basin) and the data may come from several NDP organizations. Covers turning the place and topic into catalog searches, national and statewide layers found by theme, each candidate's coverage from its record or its own service, why zero results call for rephrasing, and work split by organization.
keywords:
- level:L2
- ndp
- discovery
---

# Find NDP data for a place and topic

The NDP catalog has no working search by place or time, and organizations
describe location, time and format differently. Data is found the way a
scientist would find it: by the names and the themes, with each candidate's
coverage checked directly.

## The place and the topic as search terms

- **Place:** `resolve-region` gives bounds for coverage checks and a name list
  for searching: the place, the containing county, forest, watershed and
  state, the main features, the managing agencies.
- **Topic:** catalogs word variables in many ways (snowpack, snow depth, snow
  water equivalent; canopy, fuels, land cover, vegetation type; fire perimeters,
  burn severity, fire history; subsidence, uplift, GNSS position). The
  measurement that would answer the question (lidar, DEM, station series,
  imagery) is a search term too.

## Ways to search

`connected_data_search_ndp` combines words with AND, so short queries match more.
Queries that find different things:

- A place name alone, or with one topic word.
- A topic word or measurement with no place: national and statewide layers
  cover the region without naming it.
- An organization: `connected_data_ndp_organizations` lists publishers, and a
  search with `organization` set and a theme word lists one publisher's holdings.

**Zero results is a reason to rephrase, not a finding.** Dropping a word, a
synonym, the larger unit (county, state), the theme without the place, or the
organization without the theme each reach different records. A claim that NDP
lacks something rests on the variants tried, so the queries and their result
counts are the evidence for it. A table of candidates (title, organization,
catalog id, what it measures, resources and their kinds) keeps them comparable.

## Each candidate's coverage

Each search result carries `coverage`: the record's own `location` (a `bbox`
from whichever field it uses, with `span_degrees`) and `time` (start and end,
or only an issue date), with the source field named. Records that state
neither have `null`. Time can also appear only in the title or notes.

- A **world-wide or nation-wide box** (a large `span_degrees`) says nothing
  about the region; it is as uninformative as a missing extent.
- **No usable extent:** the source itself can answer. For a service resource
  (Esri REST, ArcGIS Feature Service, WFS, WCS, STAC), the `get-geospatial-data`
  skill's `describe_geo_service` with the region's `bbox`, then a count query
  when it stays undetermined, gives the extent. For a multi-tile raster dataset,
  `connected_data_ndp_tiles_covering` does.
- **A blank `format` is missing metadata, not an unusable file.** Many records
  leave it empty for tiled rasters and point clouds; the search result then gives
  each resource's `name_suffix` (`.img`, `.tif`, `.laz`) and tallies the suffixes.
  The suffix identifies the file, and `describe_geo_service` on one resource
  reads raster and point-cloud headers. Only a failed read shows a format is
  unusable.
- Each candidate **overlaps**, **does not overlap** or **could not be
  determined (why)**, for both space and time. All three groups are part of
  the answer.

## Several organizations

When candidates come from several organizations, each organization is an
independent branch of work. When agents can be started (`spawn_agents_parallel`),
the branches can run at the same time as children started in one call: an
`explore` child for a branch that only searches and reads, a copy of the agent
(leave out `agent`) for one that connects or fetches. Without children, the
branches' searches and reads can still go together in the same step. A branch:

- acquires through the matching path: `connected_data_connect` with only the
  covering resources (or tiles) for files; the `get-geospatial-data` tools for
  services; the organization's own plugin when one is installed;
- produces a table with its source, region, period, what was fetched, and
  caveats (completeness, units, failed links and the alternative used).

`harmonize-layers` merges branches; its coverage report says what overlaps,
what does not, and what could not be determined.

## When links fail

A hub download that returns an HTTP error, or a resource whose `format` is
blank, is a local access problem, not missing data. A record's other resources
often work: the REST service behind a hub link, the VRT behind a folder of
tiles, the point-cloud source behind a viewer link. A permission refusal from
CLIO is a decision for the person, not proof that the data is closed.