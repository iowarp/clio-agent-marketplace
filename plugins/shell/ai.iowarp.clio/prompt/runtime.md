---
id: shell.runtime
section: capabilities
when: {"tools": ["prepare_execution_runtime"]}
---
For standalone scripts, `prepare_execution_runtime` provides managed executable
paths and a fresh import check; it is not required before every turn or shell
command. Project work runs in the project's own environment.
