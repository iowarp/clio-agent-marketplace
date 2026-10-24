"""Read-only search over the connected service's conversations and workspace files."""

from clio_agent.sdk import native_tool

clio_search = native_tool("clio_search")
clio_search_read = native_tool("clio_search_read")
