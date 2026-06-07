---
id: calculator
name: Pack-local Calculator MCP
transport: stdio
install:
  method: pack-local
  path: mcp/calculator_server.py
runtime:
  args:
    - serve
tools:
  - calculator_add
trust:
  policy: explicit
env_policy:
  secrets: none
verification:
  probe: list_tools
---

# Pack-local Calculator MCP

Descriptor for a minimal pack-local MCP server. CLIO should install this
descriptor disabled, show that `calculator_add` requires explicit enablement,
and derive the stdio launch command from the pack-local install metadata.
