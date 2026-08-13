# spotter-ai

SPOTTER-AI MVP — provenance capture + agentic forensic attribution demo substrate.

A tiny deterministic plant-phenotyping pipeline (ingest -> calibrate -> segment ->
extract_traits -> predict) records every stage execution, artifact hash, and metric
to a SQLite provenance store. A campaign CLI runs batches of synthetic runs and can
inject a calibration-drift fault on demand. A FastMCP tool server ("spotter") exposes
the provenance store to an agent so it can list runs, score run health, diff two runs,
trace artifact lineage, read artifact content, wait for new runs, and quarantine a
campaign it judges compromised.

## Quick start

```bash
uv sync --extra dev
uv run python -m spotter_ai.pipeline.campaign --runs 12 --tamper-at 12
uv run pytest
```

## Layout

- `src/spotter_ai/pipeline/stages.py` — the 5 deterministic pipeline stages.
- `src/spotter_ai/pipeline/campaign.py` — CLI runner (`python -m spotter_ai.pipeline.campaign`).
- `src/spotter_ai/provenance/store.py` — SQLite schema + recording/query API.
- `src/spotter_ai/server.py` — FastMCP tool server (server name `spotter`).
