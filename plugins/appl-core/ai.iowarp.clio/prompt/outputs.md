---
id: appl-core.outputs
section: domain
---
Scripts run with `shell_bash` and `uv run`; pyarrow or DuckDB suit multi-table exports, and the `parquet` tools give quick single-file looks. Notes, code and derived data in the workspace, by default `<workspace_state>/datasets/<key>/`, leave the export as delivered. `create_artifact` delivers reports, tables and figures (workspace-relative path, `kind`, full content, `used` listing sources and derived files), and `evidence-and-claims` describes explaining evidence. `audit-dataset` delegates an independent audit; its evidence is still the thing to check before relying on it.
