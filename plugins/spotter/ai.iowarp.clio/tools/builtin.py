"""SPOTTER review tools: what the watched session did, and what its answers attended to."""

from clio_agent.sdk import native_tool

# The watched session's requests, answers, tool calls, writes and model calls since a cursor.
review_activity = native_tool("review_activity")
# Labelled sources and hottest transcript excerpts behind one quoted passage of an answer.
attention_sources = native_tool("attention_sources")
