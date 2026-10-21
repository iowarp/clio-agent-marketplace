---
name: inspect-dataset-structure
title: Inspect Dataset Structure
description: Inspect dataset structure before analysis or visualization.
---

Use this skill before answering questions about an unfamiliar scientific data
file. Identify file type, groups or tables, variable names, dimensions, row
counts, data types, coordinate fields, units, and obvious metadata.

Treat the supplied source as read-only during analysis, even if a development
copy permits writes. Adapt readers, queries and derived representations to the
observed structure. Missing fields, unfamiliar versions and incomplete metadata
do not require the source to match a fixed schema or a prescribed Python script.
Inspect what is accessible, explain uncertain mappings, and keep generated code
and outputs outside the source.

Return a compact structure summary and recommend the next expert only after the
available data surface is clear.
