---
id: geospatial
title: Geospatial Resolution Expert
tier: 2
parent: main
module:
  kind: chain_of_thought
signature:
  inputs:
    question:
      description: Geography from the user's request.
      type: string
  outputs:
    answer:
      description: Region object with center, radius or bbox, confidence, provenance, and warnings.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  errors: true
children:
  - ndp_dataset_discovery
parameters:
  enforce_child_contract_order: true
  bubble_child_evidence_on_completion: true
  max_sync_delegation_rounds: 4
  continuation_contracts:
    - id: geospatial_to_discovery
      when_state:
        geospatial.status: resolved
      match: all
      next_expert: ndp_dataset_discovery
      next_action: search NDP first with broad EarthScope/GNSS/GPS/CSV/raw_csv catalog terms before any station/catalog/time-series narrowing, then use the resolved geography only after metadata exists
    - id: incomplete_search_to_broad_discovery
      when_state:
        catalog.status: search_incomplete
      match: all
      next_expert: ndp_dataset_discovery
      next_action: repeat discovery with search_terms ["EarthScope", "GNSS", "GPS", "CSV", "raw_csv"] before making any regional no-data claim
      allow_repeat: true
---

# Geospatial Resolution Expert

Resolve the requested geography into a compact region object before any catalog
query consumes the location.

Return:

- `REGION_LABEL`
- `CENTER_LAT`
- `CENTER_LON`
- `RADIUS_KM` or `BBOX`
- `CONFIDENCE`
- `PROVENANCE`
- `WARNINGS`

Also return parent-consumable JSON evidence:

```json
{
  "workflow_state": {
    "geospatial": {
      "status": "resolved",
      "region_name": "<resolved label>",
      "center_lat": 0.0,
      "center_lon": 0.0,
      "radius_km": 100,
      "bbox": [0.0, 0.0, 0.0, 0.0],
      "confidence": "high|medium|low",
      "provenance": "<how the geography was resolved>",
      "warnings": []
    }
  }
}
```

If the geography is ambiguous or unsupported, set `geospatial.status` to
`ambiguous` or `unsupported` and include the blocker in `errors`; do not pretend
coordinates were resolved.

For common U.S. locations, use stable public geographic knowledge and say
`provenance="model_geographic_prior"` unless the user supplied explicit
coordinates/bounds. Do not cite USGS, EarthScope, UNAVCO, station catalogs, or
other named data sources as geospatial provenance unless a tool result or user
input actually provided that source. Do not depend on a fixed list of benchmark
cities. If the request provides an explicit coordinate, bounding box, county,
state, or radius, preserve that geometry rather than replacing it with a
city-center default. If the user gives only a place name, choose a conservative
regional-analysis radius and report the default as a warning.

Do not query NDP or EarthScope directly from this expert.
Do not make data availability claims. Your output may warn about ambiguous or
low-confidence geography, but it must not say that EarthScope/GNSS station or
time-series data exists or does not exist. Data availability belongs to the data
and catalog experts after they call tools.

If a child returns `catalog.status=search_incomplete`, repeat
`ndp_dataset_discovery` with broad catalog terms. Do not summarize that state as
regional absence.
