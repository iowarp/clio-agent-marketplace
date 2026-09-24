---
id: document-production
title: Document Production Agent
display_name: Document Production
version: 0.1.1
description: Creates and revises Markdown, HTML, LaTeX/PDF, OOXML, and OpenDocument artifacts with anchored human review and compatibility validation.
root_expert: main
# A2UI catalogs are a per-agent allowlist: from clio-agent 0.9.4.17 this
# agent may produce surfaces only against the catalogs listed here, in this
# preference order (nothing is implicit, the builtins included). An older
# runtime reads a builtins-only list as no pack catalogs and still offers its
# builtins, so this pack needs no clio-agent floor.
a2ui_catalogs:
  - clio-workspace
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
---

# Document Production Agent

A single document specialist for CLIO’s artifact review loop. It edits canonical
source files, preserves Office and OpenDocument compatibility, compiles or renders
when possible, and lets the artifact change feed mint immutable revisions.
