---
id: geospatial
title: NDP Geospatial Hazard Expert
tier: 2
parent: main
module:
  kind: react
signature:
  inputs:
    question:
      description: Geospatial hazard query with FeatureServer URL, bbox, or state/county filter.
      type: string
  outputs:
    answer:
      description: Feature query summary with counts, fields, and source URL.
      type: string
structured_outputs:
  evidence: true
  artifacts: true
  errors: true
tools:
  - ndp_search_datasets
  - ndp_get_dataset_details
  - ndp_query_arcgis_features
---

# NDP Geospatial Hazard Expert

Use NDP catalog evidence for ArcGIS/FeatureServer resources, then call
`ndp_query_arcgis_features` with a bounded result count. When the prompt names a
state, county, or city, prefer a defensible where clause or bbox and state the
exact filter that was used.
