---
id: remote-sensing-ogc-review
title: Remote Sensing OGC Review Agent
version: 0.1.0
description: Reviews remote sensing metadata through an explicitly enabled OGC API MCP descriptor.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/ogc_catalog.md
defaults:
  prompt_profile: heavy
---

# Remote Sensing OGC Review Agent

This agent is intentionally packaged with an MCP descriptor. CLIO should install
the descriptor as disabled, show that `ogc_features_query` needs explicit
enablement, and only surface the tool after the workspace/user enables the
descriptor.
