---
id: mcp-calculator-smoke
title: MCP Calculator Smoke Agent
version: 0.1.0
description: Minimal Agent Blueprint that packages a disabled pack-local MCP descriptor for marketplace launch-semantics validation.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
defaults:
  prompt_profile: light
---

# MCP Calculator Smoke Agent

This pack exists to validate marketplace packaging semantics for self-contained
MCP descriptors. The MCP descriptor is disabled by default and must be trusted
and enabled before its tool can be used.
