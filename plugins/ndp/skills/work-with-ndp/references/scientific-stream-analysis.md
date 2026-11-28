# Analyze streams and available history

Discovery, acquisition, continuation and analysis are the agent's work with these
tools; a scientific question is answered by evidence and interpretation, not by
a description of interface controls. A required approval or private login is a
handoff to the person; reading a public sample or using a returned continuation
value is not.

## Establish what is being delivered

Cataloged Kafka sources have configured `streaming_v2` SDK operations, returned
by `connected_data_ndp_endpoint_operations`. `SDK streaming_v2.open` takes the
exact catalog resource ID, `SDK streaming_v2.read` captures, and the retained
resource holds the capture. CLIO preserves the records returned during
SDK initialization and owns durable partition positions between finite captures.
`SDK streaming_v2.stop`/`resume` control the reader. These controls do not stop
the independent source producer. Custom Endpoint `/streams` HTTP routes are a
different path, and cursors are not for the person to copy. An SDK runtime that
is not configured is a CLIO setup requirement, not evidence that NDP refused
access or lacks data. The separately installed SDK and private broker profile run
on the connected computer or its approved SSH target; broker credentials remain
private there.

The selected catalog/resource metadata, provider documentation and actual payload
establish the producing instrument or model, variable meanings and units, time
encoding, reference frame and documented processing. They separate:

- Measured observations with a traceable acquisition source.
- Derived or preprocessed observations with documented transformations.
- Simulation, synthetic/example data, and values whose origin is unverified.

Preprocessing can be appropriate for a research question when what changed
supports the resulting variables. A filename does not make a catalog export raw
measurements, and columns named east/north/up are not physical displacement
without the required provenance, units and frame.

For a question about a physical phenomenon, unresolved observational provenance
is a limit on the scientific answer. Timestamps or bytes can diagnose the source,
and documented observations may exist elsewhere in the catalog/services. Trends,
percentile comparisons or plots of provenance-unverified values do not substitute
for the requested science; they are records or values, not
observations/measurements. A numerical data audit is a separate deliverable; it
can explain missing evidence but does not complete the physical investigation.

SSE, Kafka and a CSV file describe delivery or storage. None proves authenticity,
live acquisition or historical retention. A CSV replay emits file rows; changing
its delivery interval does not acquire new observations. A convenient replay URL
in place of an unavailable requested stream is a different source, not success.
An unrelated example works only as a separately labelled transport exercise.

## Find the historical coverage that actually exists

The requested service's advertised query, retention and continuation
capabilities, its documented time/offset bounds and measurement timestamps
establish which history can be retrieved. The oldest record in a short sample is
not necessarily the oldest retained observation. A consumer's local memory buffer
is also not the upstream historical archive.

A stream with no retrievable history may have a corresponding NDP archive. It
is compatible only when instrument, variables, processing, units and reference
frame match. The archive's identity and coverage are separate from the stream's,
and a joined source or conversion is part of the result. A different station,
demonstration file or source is not the requested one.

What each outcome means:

| Finding | Scientific consequence |
| --- | --- |
| Requested history is available and compatible | The comparison can be made over the verified dates and gaps. |
| Only a limited retention window is available | That window can be analyzed; the requested periods outside it are not covered. |
| The inspected service supplies current data only, with no compatible archive found | Historical data is unavailable through those checked sources; a new bounded capture answers only what current data can. |
| Access, service failure or missing metadata prevents checking history | Historical availability is unverified because of the actual obstacle; that is not evidence the history does not exist. |
| Only demonstration, synthetic or provenance-unverified values are available | They are not evidence about the physical phenomenon; the missing provenance or observation source is the finding. |

## Acquire, continue and analyze

`services-and-streams.md` covers the service procedures. Returned identities,
approved filters and bounded reads produce the captured bytes. Exact API cursors,
partition/offset positions and source revisions belong with the investigation.
The service's own continuation contract resumes it, and adjacent measurement
identities show repeats or gaps. A replay's row cursor and a broker's retained
offsets are not interchangeable.

Continuation is internal work. Answers describe the observations and the available
next action; opaque cursors and rerun instructions are diagnostics or low-level
reproduction detail. A missing or ambiguous completion position is an uncertainty
in the resumed data.

Results hold only for the actually acquired interval and inspected variables.
Sample counts, clocks, gaps, flags and uncertainty decide whether aggregating or
joining history is valid. The scientific analysis and interactive chart
capabilities present results. Supported conclusions, provenance/processing,
history coverage and material limitations are the substance of an answer.
Producers this investigation did not start belong to someone else.

Successful transport, a replay continuity check, loading a skill or producing a
chart is not scientific task acceptance; only evidence that answers the
question is.
