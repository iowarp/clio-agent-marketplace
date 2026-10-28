---
id: appl-core.outputs
section: domain
---
Run scripts with `shell_bash` and `uv run`; pyarrow or DuckDB suit multi-table exports, and the `parquet` tools give quick single-file looks. Write notes, code and derived data to the workspace, by default `<workspace_state>/datasets/<key>/`, so the export stays as delivered. Deliver reports, tables and figures with `create_artifact` (workspace-relative path, `kind`, full content, `used` listing sources and derived files), and explain evidence as `evidence-and-claims` describes. Delegate an independent audit with `audit-dataset` when it helps, and check its evidence before relying on it.
