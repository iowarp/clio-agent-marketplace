"""CLIO's built-in web search and page reading (the in-process ``web`` server)."""

from clio_agent.sdk import native_tool

web_search = native_tool("web_search")
web_fetch = native_tool("web_fetch")
