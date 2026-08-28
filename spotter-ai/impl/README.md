# SPOTTER forensic and provenance MCP

SPOTTER is a standalone MCP server with two complementary surfaces:

- provider-aware agentic execution and artifact-lineage queries over native JSONL, Flowcept, and CMF;
- phenotype campaign health, run comparison, lineage inspection, alerting, quarantine, and recovery.

It does not call clio-agent and it does not run or proxy the upstream Flowcept or CMF MCP servers.
Provider queries read one explicit CLIO YAML configuration and connect directly to the stores selected
there. Campaign forensics reads an existing phenotype SQLite database in read-only mode; only the
explicit alert and quarantine tools mutate their bounded sentinel files.

## Run

```console
uv sync --extra dev
uv run spotter-mcp --clio-config /workspace/.clio/config.yaml
```

`SPOTTER_CLIO_CONFIG` can provide the path when `--clio-config` is omitted.
When launching through the bundled agent pack, `SPOTTER_IMPL_DIR` must be the absolute path to this
`impl` directory.

To attach the watcher to a phenotype campaign, use the same campaign variables as the workload:

```console
SPOTTER_CAMPAIGN=phenotype-2026
SPOTTER_DB=/workspace/spotter_provenance.sqlite
SPOTTER_DATA_DIR=/workspace/campaign_data
```

The server never creates a missing campaign database. Until the workload has produced the database
and its required schema, the campaign capability reports `campaign_store_unavailable` explicitly.
The watcher can then perform one health sweep, inspect a suspicious run, raise the native alert card,
quarantine further batches, and lift quarantine only after an explicit human resolution.

## Provider configuration

```yaml
provenance:
  agentic:
    providers: [flowcept]
    query_default: flowcept
    flowcept:
      settings_path: /runtime/flowcept.yaml
  artifacts:
    provider: cmf
    cmf:
      server_url: http://127.0.0.1:8380
      pipeline_name: clio-agent
```

Flowcept queries use the MongoDB settings in the referenced Flowcept settings file. CMF queries use
the current CMF REST server. Provider credentials remain in those configuration files and are not
accepted as model-supplied MCP arguments.

For native querying, configure the journal explicitly:

```yaml
provenance:
  agentic:
    providers: [jsonl]
    query_default: jsonl
    jsonl:
      path: /runtime/provenance
  artifacts:
    provider: native
    native:
      workspace_root: /workspace
```

## Native JSONL contract

The native provider accepts either CLIO semantic-event records containing `event_type`, or the
portable Spotter record dialect:

```json
{"schema_version":"spotter.provenance.v1","record_type":"workflow","workflow_id":"wf-1","data":{"status":"completed"}}
```

Defined portable `record_type` values are `workflow`, `agent`, `task`, `pipeline`, `execution`,
`artifact`, and `model_card`. Each record stores its type-specific public fields in `data`; stable
identity fields may also appear at the top level. Pipeline and model-card tools are advertised only
when those record types are present. Unknown JSONL objects fail validation instead of being silently
treated as provenance.

## Semantics

The MCP exposes purpose-specific tools rather than a generic query endpoint. Provider selection is
not a tool argument. Each provider advertises its exact capability set, and unsupported operations
raise a structured `capability_unavailable` error. Normalized fields support cross-provider agent
reasoning; the complete source response remains under `extensions.flowcept`, `extensions.cmf`,
`extensions.clio`, or `extensions.jsonl`.

Campaign tools preserve the same explicit boundary. Inspection tools are read-only; `raise_alert`
atomically writes the campaign `QUARANTINE` sentinel and `lift_quarantine` removes it. The health
calculation is shared with the reference phenotype workload: at least eight completed peers, a one
percent relative standard-deviation floor, and an anomaly threshold of `abs(z) >= 3`. Missing stores,
schemas, runs, or artifacts return typed provenance errors instead of fabricated empty results.
