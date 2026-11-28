# Organizations, datasets, storage and publication

This reference covers catalog changes, from registering already hosted data to
publishing selected CLIO artifacts or updating an existing research collection.
`references/worked-examples.md` contains several adaptable examples.

## Intent and scope

The request and project context name the destination, organization, collection
grouping and audience. One dataset may hold many resources; independent
collections may need separate datasets. An existing collection may need an update
instead. Not every artifact is a dataset, and not every set of artifacts belongs
in one record.

`connected_data_status.ndp_endpoints` lists saved Endpoints.
`connected_data_ndp_endpoint_operations` returns the chosen Endpoint's actual
operation IDs, query/path parameters and JSON schemas;
`connected_data_ndp_endpoint_request` executes supported JSON changes. Paths below
are examples of NDP operations, not a promise every deployment implements them.

Central discovery, an Endpoint's local catalog, `pre_ckan` staging, and federation
publication are different destinations. When several writable Endpoints fit, the
intended owner is a question for the person. A similarly named publisher elsewhere
is not the same organization.

## Resolve or create an organization

`GET /organization` (with `server="local"` when advertised) lists organizations by
ID/name and display title. A name filter that misses can still leave the
organization in the full list; a spelling error is not a reason to create one.
Global catalog publishers do not prove a matching local writable organization.

`POST /organization` creates an organization; an existing match makes creation
unnecessary. A typical body is
`{"name":"coastal-lab","title":"Coastal Lab","description":"..."}`, and the
returned identity is readable back. Creating catalog ownership does not create
an authorization group, add members or grant roles. Role administration is a
separate capability and request.

Protected Endpoints use the private NDP account authorization. Anonymous
connections may need normal connection approval for `authentication="ndp"` at the
exact URL/SSH destination. A 401/403 is either a signed-out account or an
issuer/audience or role denial; the actual error says which, and repeated login
does not change a role denial. Sign-in goes through `connect-data`; credentials
do not go in tool arguments.

## Where resource bytes live

| Input | What it involves |
| --- | --- |
| Already hosted scientific files/services | Their actual stable resource locations and access requirements; registration in place needs no copy. |
| Local selected artifacts | Immutable artifact version IDs, names, sizes and SHA-256. The bytes are stored through an approved destination before their locations are registered. |
| New analysis outputs | `create_artifact` registers outputs; selected versions then follow the local-artifact path. |
| Existing dataset resources | The current record and resource IDs; changes keep their identities and unrelated metadata. |

For local artifacts, the Endpoint's storage capabilities and available buckets
decide where bytes go. `connected_data_ndp_upload_artifact(endpoint_id, artifact_id, bucket_name,
key_prefix)` requires advertised multipart `POST /s3/objects/{bucket_name}` and
object GET operations. It snapshots the exact version, checks existing bytes before
a retry, uploads when missing, and verifies a read-back. Its verified receipt and
returned `resource` descriptor are the evidence of the upload. It does not create a
bucket; generic JSON requests do not substitute for multipart upload. `POST /s3`
catalog registration, when present, describes an object; it does not upload it.

The tool handles artifacts up to 512 MiB; larger inputs need an approved bulk
transfer workflow. Missing object storage is a capability gap; installing storage
is a separate decision. Already approved hosting may fit. A record pointing at
untransferred local files points at nothing others can read.

Expiring signed URLs, credentials, `file://`, local CLIO preview URLs and an SSH
host's loopback address do not work as shared resource locations. Access conditions
belong with the data. A verified S3 URI is meaningful only with the intended
Endpoint's storage configuration; it does not imply anonymous or federated
availability.

## Create a dataset

The destination's local catalog may already hold the intended slug and
organization. `GET /search` uses array-valued terms, for example
`{"server":"local","terms":["coastal-observations-2026"]}`; the first text match
is not necessarily the exact identity. An existing record may mean retry, update,
or a genuinely distinct collection.

A discovered `POST /dataset` body built from real resource descriptors:

```json
{
  "name": "coastal-observations-2026",
  "title": "Coastal observations 2026",
  "owner_org": "RESOLVED_ORGANIZATION_ID",
  "notes": "Coverage, variables, units, methods and provenance for this collection.",
  "private": true,
  "resources": [
    {"url": "VERIFIED_STABLE_LOCATION", "name": "observations.nc", "format": "NETCDF"}
  ]
}
```

This is an illustrative shape, not a fixed resource count or required scientific
description; the schema and actual contents decide it. The display title and stable
lowercase slug are different fields. `owner_org` is the publisher, not a role.
Supported tags, license, version and provenance metadata come from what the
research project established; units, licenses and access claims not established
there are invented.

Visibility is the person's choice. When the person has not named an audience for
new results, private (where supported) exposes nothing they did not intend. An
Endpoint that cannot honor the requested visibility cannot create the record as
asked. Catalog visibility and object access controls are separate. An existing
dataset's visibility is part of what an edit preserves.

`scripts/prepare_dataset.py` assembles this body from any number of selected upload
receipts and/or hosted resource descriptors. It separates provenance from the
request body; it performs no network writes. It helps when assembling resources;
a small metadata edit does not need it.

Some NDP deployments auto-rename conflicting names, so the **returned** IDs, names
and titles, not the requested slug, are the final identity; the response also
carries warnings.

## Update metadata or resources

The exact dataset record, and its PATCH/PUT and resource-specific operations, show
what an update can do. An advertised resource-add operation adds a resource;
otherwise a merge with the existing resource array, preserving IDs and unrelated
entries, does. Arrays may replace the collection rather than append. Replacing an
existing file version also involves a storage/version policy; a title change alone
is metadata.

Unspecified fields, visibility, resource IDs and supported provenance survive an
edit only if the request carries them. Recreating a dataset to edit it changes its
identity. Without a catalog version model, selected content hashes and explicit
version metadata record versions, but that is not native version history. Deleting
a catalog resource, deleting its stored bytes, and removing a CLIO connection are
different actions with different destructive scope.

## Verify, publish and recover

An advertised detail route or local search reads the exact record back: organization,
final name/title, visibility, requested metadata and resource identities/locations.
Stored artifacts have a verified hash/size; hosted data has whatever access check
was actually performed. Metadata read-back does not establish that another user's
account can read bytes.

Local creation is not federation publication. The semantics of
`POST /dataset/{dataset_id}/publish` vary: the observed NDP Endpoint advertises
**local catalog to PRE-CKAN**, not immediate global publication. Other deployments
may differ. A returned publication identity, and a read back from the destination,
show what happened. Central visibility shows only in central discovery, and may
lag as staging/propagation. Changing the audience to make private research
discoverable changes what the person chose to share.

After a timeout or dropped POST response, the write may or may not have happened;
a read by slug, organization and resources tells which and avoids duplicate records.
Recorded object/record identities let partial work resume; an uploaded object is
not a completed dataset. Shared objects may be used elsewhere, so deleting them is
not a safe rollback. Write state is uncertain until a read resolves it.

The resulting collection, organization, destination, visibility and verified
resources are what the person needs; a returned/documented catalog page, or its
stable identity, locates it. Request schemas and receipts are supporting detail,
not the person's workflow.

## Register a URL, S3 object, service or topic

Some deployments provide convenience registrations in addition to `POST /dataset`:
`POST /url`, `/s3`, `/services` and `/kafka`, each with its own schema and
collection effects. A route called “add resource” may create its own catalog
package; it is not necessarily an append operation for an existing dataset. The
dataset update procedure is what preserves an existing collection.

URL/S3 registration describes existing hosted bytes. Service registration describes
an existing callable API, not a service install. The observed `/services` schema
requires `owner_org="services"`, a deployment constraint that an arbitrary
research organization does not satisfy. Topic registration describes the
requested Kafka resource; it does not create a broker, start acquisition, or
consume messages, and a route name does not reveal its effects. Reading back the
record and testing the data operation are separate checks of metadata and data.
