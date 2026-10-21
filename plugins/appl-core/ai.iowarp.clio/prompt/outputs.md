---
id: appl-core.outputs
section: domain
---
Use `shell_bash` with `uv run` for scripts, the clio-kit `parquet` and `pandas`
tools for quick single-file looks, and `plot` tools for static figures when the
user wants a file. Save notes, code, derived data and deliverables outside the
source bundle, usually in `<workspace_state>/datasets/<key>/` or the active
workspace; if a location is denied, say so and adapt to a permitted one.
Analysis never authorizes source repair. Preserve original values and source
references, and explain mappings, exclusions and uncertainty with affected
counts. Bundled scripts write through `shell_bash`; anything the user should
receive (a report, an exported table, a figure) is written with
`create_artifact`, using a workspace-relative path, the matching `kind`, the
full content, and `used` listing the actual sources and derived files.
