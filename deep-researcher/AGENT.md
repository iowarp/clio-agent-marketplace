---
id: deep-researcher
title: Deep Researcher
display_name: Deep Researcher
version: 0.1.0
description: Model-agnostic, agent-driven deep web research. A flat coordinator dynamically fans out as many web researchers as the question needs, sends the assembled evidence through an independent web-enabled critic, closes material gaps, and creates a clean Markdown report artifact with inline citations and an auditable source ledger. CLIO alone controls runtime concurrency and queues excess work; the blueprint declares no workflow, worker count, research-round limit, or paid search provider.
root_expert: main
blueprint:
  format: agent-blueprint-v1
# The installed clio-kit launcher avoids concurrent `uvx` environment creation races.
# Provider selection belongs to deployment configuration. A self-hosted deployment can use:
# WEB_SEARCH_PROVIDER=searxng and WEB_SEARXNG_BASE_URL=<instance root>.
mcp_servers:
  web: clio-kit mcp-server web
experts:
  - experts/main.md
  - experts/researcher.md
  - experts/critic.md
---

# Deep Researcher

This Agent Blueprint performs open-ended, source-grounded web research with a
flat agent-as-tool topology. `main` is the sole coordinator and final-answer
author. It may spawn any number of direct `researcher` and `critic` child turns,
including repeated concurrent runs of the same child, according to the question
and the evidence still missing.

The Agent owns research breadth, decomposition, follow-up rounds, and semantic
stopping. CLIO owns admission, concurrency, queueing, and other infrastructure
backstops. A queued child is accepted work waiting for capacity, not failed work
and not a signal that the research plan should be reduced.

Every successful run produces a durable Markdown report artifact, not only a chat
answer. Sources whose fetched content influenced the report are cited inline at
the claims they support and recorded in its source ledger. Fetched sources that
were not used are retained separately with their disposition, so discovery,
reading, evidence use, and citation remain distinguishable.

Search-provider selection is deliberately not embedded in the blueprint. The web
MCP uses its deployment configuration, so operators can select a local SearXNG
instance without supplying Brave, Tavily, or other paid-provider credentials.
