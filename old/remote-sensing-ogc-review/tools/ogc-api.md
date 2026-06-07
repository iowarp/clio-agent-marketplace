---
id: ogc-api
name: OGC API Features MCP
transport: stdio
command: ogc-api-mcp
args:
  - serve
tools:
  - ogc_features_query
---

# OGC API Features MCP

Descriptor for an OGC API Features MCP server. The descriptor is configuration
only; CLIO must install it disabled and require explicit enablement before the
tool can be used.
