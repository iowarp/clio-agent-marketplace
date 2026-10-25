# SPOTTER provenance MCP

SPOTTER is a standalone MCP server for the `spotter-ai` watcher with two read-only surfaces:

- provider-aware agentic execution and artifact-lineage queries over native JSONL, Flowcept, and CMF;
- captured model-attention inspection for one watched session.

It does not call clio-agent and it does not run or proxy the upstream Flowcept or CMF MCP servers.
Provider queries read one explicit CLIO YAML configuration and connect directly to the stores selected
there. No tool writes to a store.

Alerts and containment belong to CLIO, not to this server. The watcher raises an alert with CLIO's
`raise_alert_card` tool, and CLIO's SPOTTER clearance holds the watched session's next mutating call
until the watcher's review has settled; the person decides what happens next.

## Run

```console
uv sync --extra dev
uv run spotter-mcp --clio-config /path/to/clio-provenance-handoff.yaml
```

`SPOTTER_CLIO_CONFIG` can provide the path when `--clio-config` is omitted.
When launching through the `spotter` plugin, clio-agent supplies both launcher inputs: the plugin
directory (`${PLUGIN_ROOT}`, whose `impl` project this is) and its effective provenance
configuration as a CLIO YAML file (`${CLIO_PROVENANCE_CONFIG}`).

## Provider configuration

### Captured attention

`list_attention_calls(session_id)` lists recorded response identities.
`inspect_attention(response_id, steps, profile)` verifies the descriptor's local
SafeTensors file, then reduces the selected decode-step rows with the same pinned
`clio-schemas` implementation as CLIO. Overlapping steps count once. Profile heat
and uniform mean attention mass are separate, and every response carries the
resolved profile and its revision hash.

Enable Flowcept among the provenance providers and set the explicit local capture
root using the dotted YAML key `provenance.attention.files_dir: /data/clio/attention`.
This works even when general provenance queries default to native JSONL. CLIO's
effective handoff supplies the root when attention capture is enabled. An explicitly
staged local mirror may retain the connector's `<workflow>/<filename>` layout;
SPOTTER never fetches capture files over SSH or reads outside the configured root.

The tool returns captured token coordinates and coverage, not guessed transcript
or image coordinates. Use recorded decode-step mappings; do not estimate them from
character offsets. Missing sparse values are unretained, not measured zero.
Attention strength alone is not evidence of poisoning. Delta fresh-inference and
reviewer demo qualification remain required before publication.

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
