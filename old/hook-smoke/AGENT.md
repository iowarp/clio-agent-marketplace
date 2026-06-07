---
id: hook-smoke
title: Packaged Hook Smoke Agent
version: 0.1.0
description: Minimal Agent Blueprint for packaged hook discovery, trust, enablement, and invocation evidence.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
defaults:
  prompt_profile: light
---

# Packaged Hook Smoke Agent

This pack validates CLIO marketplace semantics for packaged runtime hooks. The
hook descriptor is disabled by default and must be explicitly trusted and
enabled before it can affect a session.
