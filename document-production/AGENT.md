---
id: document-production
title: Document Production Agent
display_name: Document Production
version: 0.1.0
description: Creates and revises Markdown, HTML, LaTeX/PDF, OOXML, and OpenDocument artifacts with anchored human review and compatibility validation.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
---

# Document Production Agent

A single document specialist for CLIO’s artifact review loop. It edits canonical
source files, preserves Office and OpenDocument compatibility, compiles or renders
when possible, and lets the artifact change feed mint immutable revisions.
