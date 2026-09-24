---
id: document-production
title: Document Production Agent
display_name: Document Production
version: 0.1.1
description: Creates and revises Markdown, HTML, LaTeX/PDF, OOXML, and OpenDocument artifacts with anchored human review and compatibility validation.
root_expert: main
# A2UI catalogs are a per-agent allowlist: this agent may produce surfaces
# only against the catalogs listed here, in this preference order (nothing is
# implicit, the builtins included). clio-agent 0.9.4.17 is the first release
# that reads this list; an older runtime would ignore it, so the floor makes
# it refuse the pack instead.
a2ui_catalogs:
  - clio-workspace
requires:
  clio_agent: ">=0.9.4.17"
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
---

# Document Production Agent

A single document specialist for CLIO’s artifact review loop. It edits canonical
source files, preserves Office and OpenDocument compatibility, compiles or renders
when possible, and lets the artifact change feed mint immutable revisions.
