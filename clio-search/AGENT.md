---
id: clio-search
title: CLIO Search
display_name: CLIO Search
version: 0.1.0
description: Read-only answers and discovery across the connected CLIO service's conversations, message passages, and workspace files, with real navigable source links.
root_expert: search
a2ui_catalogs:
  - clio-workspace
requires:
  clio_agent: ">=0.9.5b3"
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/search.md
---

# CLIO Search

Press Tab in CLIO's search box to select this assistant, then Enter to ask.
The connected service creates a separate read-only search conversation and uses
the model selected for CLIO Search in Settings > Fleet. With no override it
inherits the current conversation's model, then the service default.

The assistant can discover registered conversations, matching message passages,
and files in the connected service's workspaces. It reads bounded evidence and
returns actual internal links. Searches do not alter the conversation you were
viewing or the files they find. Closing search deletes its temporary conversation.
It does not search other CLIO services, unregistered directories, or the web.

File-content searches have explicit read and scan limits. Policy-denied sources,
binary files, truncated excerpts, and incomplete scans must remain visible as
limitations rather than becoming claims that a source does not exist.
