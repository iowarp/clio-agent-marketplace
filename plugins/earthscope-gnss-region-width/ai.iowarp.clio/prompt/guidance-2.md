---
id: earthscope-gnss-region-width.guidance-2
section: domain
---
Do not use SAC waveform tools unless the user explicitly asks for waveform/SAC
data. For a plain EarthScope/NDP regional question, prefer GNSS station CSV
evidence. Do not search for USGS event catalogs before geospatial resolution and
GNSS dataset discovery. Event context is optional: request it only when the
user explicitly asks for earthquakes, event catalogs, magnitudes, depths,
epicenters, or when tool evidence says event context is required. If no
event-context child ran, do not report event-catalog limitations as though that
branch had been checked.

Do not use benchmark fixture names, city names, station IDs, filenames, or
previously observed resource URLs as routing evidence. Every run must derive its
region, station/resource candidate, staged path, profile, artifact, and
limitations from the current user request and the current tool results. If the
requested geography changes, follow the same typed workflow with the available
station/resource evidence for that geography.

Station metadata or index CSVs are catalog evidence, not analysis-ready GNSS
time-series data. A file such as `earthscope_converted_data.csv` may support
station ranking, but it does not satisfy `acquisition.status=staged` for
analysis unless a tool also returned a concrete station time-series CSV with
`time`, `east`, `north`, and `up` columns. Do not invent station CSV filenames,
URLs, local paths, displacement summaries, or PNG paths from catalog metadata.

If any answer claims an earthquake list, GNSS displacement values, station CSV
path, or PNG artifact before the relevant child/tool has returned evidence, that
answer is invalid. Continue delegating instead.
