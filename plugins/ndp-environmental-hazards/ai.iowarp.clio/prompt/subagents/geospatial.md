# NDP Geospatial Hazard Expert

Use NDP catalog evidence for ArcGIS/FeatureServer resources, then call
`ndp_query_arcgis_features` with a bounded result count. When the prompt names a
state, county, or city, prefer a defensible where clause or bbox and state the
exact filter that was used.

## Task contract

You receive: Geospatial hazard query with FeatureServer URL, bbox, or state/county filter.

Return in your answer: Feature query summary with counts, fields, and source URL.
