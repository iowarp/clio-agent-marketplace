---
id: earthscope-gnss.answer-templates
section: domain
---
**Positive run (a station was staged)** — write the answer as:

```
## Region
<resolved region + center/radius, in prose>

## Station selected
Station **<catalog code, e.g. P475>** — the only station staged and analyzed;
distance/network only if upstream reported them.

## Data resource
- Staged CSV: `<exact acquisition.local_path>`
- Source URL: <exact acquisition.source_url>

## Profile evidence
<rows scanned/profiled, columns, uncertainty ranges — grounded numbers only>

## Visualization
- PNG: `<exact artifact.path>` — what it shows.

## Freshness, coverage & provenance limitations
<prose>
```

**Data-blocked / no-coverage run (honest negative).** If the accumulated state
has NO staged analysis-ready station CSV (no `acquisition.status=staged` +
`analysis_ready=true` + real `local_path`) — whether staging was blocked,
metadata-only, or the region genuinely has no in-region station
(`station_catalog.status=no_candidates`) — do NOT invent one to look complete.
Drop the Station/Data/Profile/Visualization sections and write an honest prose
brief stating how far the pipeline reached and the missing/failed step. No
station, no path, no displacement stats. (You may note the distance to the
nearest outside-region station only if upstream reported it, but never name it or
present it as the region's data.) "No analysis-ready EarthScope GNSS station in
the requested region" is the correct answer; a distant or invented station
dressed up as coverage is a failure. Ignore any stray upstream
`selected_station`/`candidates`/`assessment` block whose code/path doesn't match
`resource_candidate.station_id` + `acquisition.local_path` — that is an upstream
hallucination; cite only the grounded staged station.
