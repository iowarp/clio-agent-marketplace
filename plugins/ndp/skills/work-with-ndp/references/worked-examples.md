# Adaptable NDP workflows and runnable helpers

These are independent examples, not a sequence to enact on every request.
Uppercase identifiers in tool examples mean values returned by previous tools.
Actual operations and schemas vary by deployment. Bundled fixtures are synthetic;
their locations and organizations are not real publication destinations.

## 1. Find scientific data and produce a checked result

Request: “Find EarthScope GNSS data for WWMT, compare the vertical displacement
over the available interval, and make a chart.”

```text
connected_data_status()
connected_data_ndp_organizations(query="earthscope")
connected_data_search_ndp(query="WWMT", organization=PUBLISHER_ID,
                          endpoint_id=CATALOG_ENDPOINT_ID)
```

The actual resources and their coverage show which is the measurement resource
(not its thumbnail or dashboard link); refining or paging may be needed. The
returned dataset/resource selection connects as in `discovery-and-analysis.md`;
private sign-in appears only if the data needs it. Indexing completes, the
approved relative paths list, and the selected file downloads for analysis as a
task with its own result.

Time/component encodings, units, gaps and reference conventions decide what the
coverage supports. The chart, looked at, is registered with a source/method
report. Station metadata or a preview image alone is not a displacement series;
the available evidence is what it is.

## 2. Create an organization, then register already hosted research

Request: “Create Coastal Lab on this Endpoint and catalog our existing NetCDF
observations with their methods document. Keep the dataset private.”

The Endpoint's organization and dataset operations, and its local organizations,
show whether an exact match exists (a retry) or the requested organization is
created and read back. The two supplied hosted resource locations and their
metadata describe the resources. Registration need not copy already hosted bytes.

For a local preparation demonstration, `SKILL_DIR` is the resolved directory
returned by `load_skill`. The helpers run with the available Python executable,
use only its standard library and install nothing:

```text
python "SKILL_DIR/scripts/prepare_dataset.py" --name coastal-observations-2026 --title "Coastal observations 2026" --organization coastal-lab --resources "SKILL_DIR/examples/hosted-resources.json"
```

This prints a private dataset body with **two** resources and an evidence section
explicitly marking both locations unchecked. The example.org locations are
illustrative. Real work uses inspected real descriptors saved as a workspace JSON
array. The output's `dataset` object is the request body, to be checked against
the observed Endpoint schema; `evidence` stays local. The returned dataset reads
back. A successfully prepared body or local metadata record shows neither file
access nor federation publication.

## 3. Store selected artifacts in a requested collection

Request: “Take these three artifacts and create ‘TO Optimization dataset 1’ in
Gnosis.” This particular request asks for one dataset with three resources. A
request for two independent collections or additions to an existing dataset
requires different grouping; this example is not a rule.

The selected artifact versions and existing local organization (including
plausible spelling differences), the storage and the chosen existing bucket are
resolved first, since the upload needs them. For each selected artifact:

```text
connected_data_ndp_upload_artifact(endpoint_id=WRITE_ENDPOINT_ID,
  artifact_id=SELECTED_VERSION_ID, bucket_name=SELECTED_BUCKET,
  key_prefix=PROJECT_PREFIX)
```

Each returned verified receipt saves as workspace JSON. The helper can combine any
number of receipts; for this request:

```text
python "SKILL_DIR/scripts/prepare_dataset.py" --name to-optimization-dataset-1 --title "TO Optimization dataset 1" --organization RESOLVED_GNOSIS_ID --receipt result-a.json --receipt result-b.json --receipt result-c.json
```

The body and visibility are checked, the requested collection is created and read
back, and each artifact/version/hash stays associated with the returned resource
identity. If Gnosis or storage is absent, that is a missing prerequisite; another
organization, installed storage or a manufactured result would not be what was
asked.

The helper also accepts both `--receipt` and `--resources` for a collection mixing
newly stored outputs and existing hosted material. It prepares **new** records;
for an existing dataset the update procedure applies, since a freshly generated
body would replace its resources.

## 4. Add a resource and edit metadata without replacing a collection

Request: “Add this revised calibration table to the existing estuary dataset,
keep the original observations, and correct the description.”

The exact record and organization, resource IDs and visibility come first, then
the selected calibration artifact (stored) or its stable hosted URL. Supported
resource-add/PATCH operations decide the change: a resource-specific operation if
available, otherwise a merged array preserving the existing resource IDs and
unrelated fields, with only the requested metadata changed. The record read back
shows the original observations alongside the added calibration resource. A lost
response means read before retry, not another POST.

Replacing a resource version is a different request with its own
identity/version policy; old bytes kept or deleted as a side effect would be
unasked-for.

## 5. Query station metadata through an SSH Endpoint

Request: “Use the Ares NDP service to find metadata for IU.ANMO.”

A saved Ares connection is reused; if none is saved and the person selected that
host/service, the existing service connects:

```text
connected_data_ndp_endpoint_connect(name="Ares NDP",
  url="http://127.0.0.1:8002", ssh_profile="ares", authentication="none")
connected_data_ndp_endpoint_operations(endpoint_id=SERVICE_CONNECTION_ID,
  query="search")
```

The observed local catalog search with `terms=["earthscope"]` and
`server="local"` gives the actual service identifier. If its service proxy
is advertised, the request is:

```text
connected_data_ndp_endpoint_request(endpoint_id=SERVICE_CONNECTION_ID,
  operation_id=OBSERVED_SERVICE_PROXY_OPERATION,
  parameters={"service_identifier": RETURNED_SERVICE_IDENTIFIER, "path": "query",
              "query": {"net":"IU", "sta":"ANMO", "level":"station", "format":"text"}})
```

The captured `resource_id` reads directly, or its materialized path inspects:

```text
python "SKILL_DIR/scripts/inspect_capture.py" "CAPTURE_WORKSPACE_PATH" --sha256 CAPTURE_SHA256
```

For FDSN station text this reports pipe-delimited columns, actual row count,
missing cells and sample rows. Station epochs are not repeated samples;
this result is metadata, not a waveform read or a new stream producer.

## 6. Sample archived data, inspect and resume

Request: “Show a short sample from this archived CSV stream, then the next segment.”

An actual archived file or approved URL the person supplied, and the on-demand
service's segment schema, give a finite segment. Its captured data holds the
`done` cursor for the next request. Measurement identities/timestamps at the
boundary show continuity; control events are not measurements.

The fixture demonstrates parsing without contacting or starting any service:

```text
python "SKILL_DIR/scripts/inspect_capture.py" "SKILL_DIR/examples/replay-segment.sse"
```

Expected: four complete events (`hello`, two `sample`, `done`), no incomplete
event, resume cursor `row:44`, and last event ID `43`. The ID and cursor differ.
The sample timestamps are from 2020: this is archived replay, regardless of when
the capture is made. An incomplete final event is flagged and not counted.

Live acquisition has the separate producer lifecycle in `services-and-streams.md`:
actual station codes/topic, a started session with its identity and status, its
consumed output, and the specific producer stopped when finished. The finite read
channel closing does not stop it.

## Helper interpretation

Both scripts print JSON to stdout and leave inputs unchanged; redirecting to a new
workspace file retains the report. Invalid input, hash mismatch, oversized capture
or unverified upload receipts return a nonzero status, and the prepared body is
then partial. `inspect_capture.py --format` can override
auto detection; `--delimiter` handles known delimited formats. Binary HDF5,
NetCDF, MiniSEED and large files need their proper readers, not this text helper.

Prepared metadata is not a remote mutation; a stored receipt is evidence from the
upload tool, not independent credential verification by the helper. Shape/hash
inspection does not validate scientific units, freshness or another account's
access. Each example differs from the actual request, selected data and deployment.
