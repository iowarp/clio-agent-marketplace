---
id: earthscope-flat.answer-provenance
section: domain
---
Audit source authority for geographic provenance. If geospatial state says
`provenance=model_geographic_prior`, do not cite USGS, UNAVCO, EarthScope,
station metadata, downloaded shapefiles, or other named external sources for the
region geometry. Say the region was approximated from model geographic knowledge
or user-provided coordinates. Named source provenance is allowed only when a tool
result or the user explicitly supplied that source.

A turn that ran a fresh pipeline reports its facts — region, station, staged
path, profile numbers, artifact path, limitations — each with its provenance. A
follow-up turn answers only what was asked, citing the earlier facts without
restating them.
