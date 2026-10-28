"""SPOTTER review tools: what the watched session did, and what its answers attended to."""

from clio_agent.sdk import native_tool

# The watched session's requests, answers, tool calls, writes and model calls since a cursor.
review_activity = native_tool("review_activity")
# Labelled sources and hottest excerpts behind an answer (the whole answer or a quoted passage).
attention_sources = native_tool("attention_sources")
