# Find, access and analyze scientific data

## Discover an appropriate collection

A research question has a phenomenon/variable, place or station, time interval,
resolution and desired output; these determine which collection fits.

- `connected_data_status` shows approved resource selections and
  `open_references`, catalogs in `ndp_catalogs`, and services in `ndp_endpoints`.
- `connected_data_ndp_organizations(query="earthscope")` resolves a publisher;
  its returned `id` and `endpoint_id` are the values a search takes (an
  organization slug is not guessable).
- `connected_data_search_ndp(query=..., organization=..., endpoint_id=...)`
  matches metadata, not every value in the underlying data. A broad query shows
  naming conventions; actual station codes, titles, descriptions and formats
  narrow it.
- Candidate resources differ: measurement files, derived products, images,
  notebooks, service descriptions and live/replay links. A familiar station name
  does not guarantee the requested variable or time interval.

Values can be measured, derived, simulated or provenance-unverified. A `raw_csv`
path or a catalog's publisher label is insufficient to establish instrument
observations; documented processing and scientific metadata are what establish
it. Derived data can be valid when its meaning and transformations support the
question. `scientific-stream-analysis.md` covers stream/history comparisons,
including the distinction between unavailable history and a failed attempt to
establish availability.

Each agent search page holds up to 50 datasets. The returned `next_offset`, with
the same query/publisher/Endpoint, gives the next page; the first page is not the
entire catalog. Total counts are metadata, not proof that every resource is
accessible. Catalog publishers are not account groups, and filtering by one does
not grant protected access.

Central discovery holds published collections; an approved Endpoint's local
catalog holds unpublished/local holdings or services. A failed central search has
an actual error to read; a local catalog is a different scope, not a transparent
substitute. Scanning every Endpoint or downloading a whole collection to populate
choices costs far more than the choice needs.

## Attach only the selected resources

The IDs are the ones the tools returned:

A source contains exactly its selected resources, not every resource in the
dataset. Another measurement or README comes from connecting that returned
resource set, under the new connection's source ID. An existing source for the
same dataset may contain a different selection; a missing selected path is not
an upstream availability failure.

```text
connected_data_connect(
  provider="ndp", root=DATASET_ID, label=DATASET_TITLE, mode="read_only",
  configuration={"endpoint_id": CATALOG_ENDPOINT_ID,
                 "resource_ids": [SELECTED_RESOURCE_ID]})
```

`CATALOG_ENDPOINT_ID` comes from the dataset search. It is not necessarily a saved
service connection ID. Public data can work without sign-in. Sign-in goes through
`connect-data` and the saved NDP account's private `login_action`; after the
person signs in, the same connection succeeds. An account can be
connected while a particular resource still denies access. Issuer/role errors
are what they say; they do not reveal or change group membership.

Connection starts indexing, not a full download. Indexing runs as a durable task
whose result comes through the normal task result tools. Then
`connected_data_open(source_id=SOURCE_ID)` lists approved relative paths (200 per
page). Attachment `revision`, `linked` and `folder`, passed back on listing/reads,
keep a changed selection from silently substituting a different revision.

The completed index supplies the linked manifest; it has not fetched file bodies.
This index reads with `linked=true`; `linked=false` reads exist only after a
Download has completed, and the linked revision does not apply to a downloaded
read. `connected_data_open(source_id=SOURCE_ID, path=RELATIVE_PATH, ...)` reads
the selected path through the link, and its immutable `resource_id` works with
`workspace_resource_read` or `workspace_resource_inspect`. Linked paths are virtual
references, not shell mounts.

## Materialize and analyze

`connected_data_open(source_id=SOURCE_ID, path=RELATIVE_PATH, range=true)` reads
part of a large file: its `handle_url` goes to the reader (for a raster,
`/vsicurl/HANDLE_URL` in GDAL or rasterio with a window). For Python or shell
analysis of a whole file,
`connected_data_download(source_id=SOURCE_ID, selected_paths=[RELATIVE_PATH])`
returns the materialized path on completion; source folder paths are not
guessable, and an accepted download keeps running without resubmission. NDP
originals stay intact; derivatives live separately in the workspace. A downloaded
historical copy is not a current upstream read after disconnection.

Downloads stream in bounded chunks; the free disk, not a fixed size, decides. Capacity,
cancellation and complete-snapshot publication belong to the transfer task; its
success does not mean the file was loaded into the model or into RAM. A linked open copies the file after checking the free disk; a large file can be
read in part by range, or downloaded and processed incrementally. An unbounded
dataframe of a large file exhausts memory; the needed columns, intervals and
aggregates are usually small. A transfer-limit error is a CLIO size limit, not an
NDP access denial.

The returned downloaded input path reads directly, even when CLIO stores
it outside the workspace root. Shell `access_paths` requests broader folder
permissions; it is not needed to read these approved inputs and cannot authorize
writes to protected source snapshots. Scripts, outputs and temporary work are
writable under the workspace. Selected measurements that lack the needed coverage
are not a collection-wide gap; other resources in the collection may cover it.
The instruments and intervals examined bound what a result can claim.

The analysis that fits depends on the actual data, not the format:

| Data | What matters before computing |
| --- | --- |
| Time series | Measurement time vs capture time, timezone/epoch encoding, cadence, gaps, duplicates, component names and units. GNSS components may differ in scaling and reference frame. |
| Instrument log / packet archive | A stored record may contain zero, one or several measurement frames. Framing and device timestamps separate complete frames from duplicates/truncation. Envelope/readout time and record count are not automatically measurement time and sample count. |
| HDF5 / NetCDF / array output | Group/variable names, dimensions, coordinate conventions, units, fill values, chunking and requested subset. Metadata is readable without reading an entire large array. |
| Spatial/station records | Coordinate reference, channel/network/station identifiers, geometry and station epochs. Metadata rows are not waveform or displacement samples. |
| Service or stream response | Actual payload schema, status/control events, measurement timestamps and whether data is replay or current acquisition. See `services-and-streams.md`. |

Repeated measurement fields can represent successive frames, not duplicate
metadata keys; reducing them to the first or last value in a dictionary loses
frames. An aggregate depends on which clock and observation unit it uses, and the
logical sample counts decide whether instruments align and which observations
are missing.

Installed readers and the analysis/visualization skills read measurements;
downloaded notebooks and serialized executable objects run code when opened.
Input dataset/resource IDs, source revision and content hashes, query filters,
units and transformations are what make a result reproducible. Reports, tables
and figures can be registered as artifacts; a figure is reviewed only once it
has been looked at. A comparison often answers what a dashboard would.

## Interpret failures

- **No matches:** broader terms, publisher naming and coverage often find it. An
  empty successful result differs from a failed search.
- **503 / timeout:** the query and actual error identify the outage; bounded retry
  or narrower paging can help. A server outage is not an empty catalog, and
  reconnecting the account does not fix it.
- **Sign-in required / 401 / 403:** saved account state, destination/issuer
  compatibility and resource/Endpoint authorization are separate causes.
  Successful browser SSO alone is not the private CLIO grant.
- **Only a preview/service link:** it supplies what its service does; the service
  route reads it. A data-file URL built from its filename does not exist.
- **Partial download or changed revision:** the accepted task's result and exact
  source identity show which files are verified; a changed input means the full
  selection has not been analyzed.

Found metadata, obtained bytes and checked analysis are separate evidence; none
substitutes for the next.
