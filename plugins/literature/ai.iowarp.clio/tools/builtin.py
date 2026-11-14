"""CLIO's built-in scholarly search and lookup (the in-process ``literature`` server)."""

from clio_agent.sdk import native_tool

literature_search = native_tool("literature_search")
literature_lookup = native_tool("literature_lookup")
