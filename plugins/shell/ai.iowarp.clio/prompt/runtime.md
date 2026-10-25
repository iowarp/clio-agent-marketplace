---
id: shell.runtime
section: capabilities
when: {"tools": ["prepare_execution_runtime"]}
---
For standalone scripts, use `prepare_execution_runtime` when managed executable
paths or a fresh import check are needed; it is not required before every turn
or shell command. Use the project's own environment for project work.
