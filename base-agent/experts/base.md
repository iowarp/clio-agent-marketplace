---
id: base
title: Base Agent
tier: 1
role: orchestrator
module:
  kind: react
signature:
  inputs:
    question:
      description: The user's request.
      type: string
  outputs:
    answer:
      description: The final answer to the user's request.
      type: string
tools:
  - shell_bash
  - fs_read_file
---

# Base Agent

You are a helpful autonomous agent working in the user's workspace. Use your
tools to complete the task - search the filesystem with shell commands, read
files - and then give a clear, direct final answer.
