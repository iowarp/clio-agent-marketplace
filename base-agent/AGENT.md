---
id: base-agent
title: Base Agent
display_name: Base Agent
version: 0.1.0
description: A single plain agent with filesystem and shell tools. No experts, no routing - a clean TTFT baseline.
root_expert: base
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/base.md
---

# Base Agent

One agent, native tools (shell + file read), raw prompt. No experts, no
routing, no workflow chrome - the clean TTFT/latency baseline for any model.

## The needle case (reproducible baseline)

1. Drop a `needle.md` in the workspace root containing a known number.
2. Attach this blueprint to a fresh session.
3. Ask: "Somewhere in this workspace there is a file named needle.md. Find
   it and tell me the number written inside it."
4. The run should take 2-4 LM calls (list/search, read, answer). Per-call
   TTFT from the stream audit log is the model's clean agent baseline,
   free of delegation resets and child spawn costs.
