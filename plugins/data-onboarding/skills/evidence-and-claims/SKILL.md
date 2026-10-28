---
name: evidence-and-claims
title: Evidence and Claims
description: Explain what source documents say, what the analysis checked, and what remains uncertain in natural language, with specific clickable supporting references. Use for findings, reports and optional experiment notes.
keywords:
- level:L0
- provenance
- uncertainty
---

# Evidence and claims

Make the answer easy to read and easy to inspect. Explain the evidence in ordinary
sentences; do not prefix every claim with bracketed status labels or append a
generic source list to every paragraph.

- **Source documentation:** "The protocol describes this measurement as projected
  area." Link the inspected protocol and name the relevant section. Documentation
  can be stale or wrong; distinguish its description from an independent check.
- **Data checks:** "I counted the distinct sample identifiers in the inspected table." Link
  the actual table and identify the key/count calculation and relevant recorded
  output. A sampled check supports a statement about the sample, not the full table.
- **Interpretation:** "This suggests a measurement ceiling, but calibration is
  still needed to distinguish it from a biological plateau." Give the evidence,
  competing explanation and what would resolve the uncertainty.

A short citation at the end of the supported sentence or paragraph is fine.
Prefer a meaningful clickable label, such as the protocol name or measurement
table, using the file/reference link format supplied by CLIO. Use an actual
inspected file's precise path or returned artifact/resource reference, never a
guessed filename. Bare backticked names are not clickable citations. If a source
cannot be opened through the available reference mechanism, say so plainly;
do not fabricate a link or claim the reader can open it.

## Match the evidence to the claim

- A manifest can support export identity or a declared file list. A README can
  support a documented definition. Neither establishes actual row counts,
  calibration, data quality, a computed effect or successful onboarding.
- Cite the relevant table, columns and calculation for a computed result. Retain
  source references, relevant input/output versions and the actual result used.
  A saved analysis report can help when its evidence and assumptions were checked.
- A `card.py status` receipt describes a saved record's status. It does not verify
  a scientific finding. "Audit in progress" is a progress update, not a source.
  An ended child turn also does not establish that its assignment succeeded.
- Use a completed audit only after inspecting its actual findings and supporting
  references. Cite those results and their underlying sources rather than the
  mere existence of an audit task. Repeat selected calculations when warranted.
- Never cite a document you did not inspect or attach unrelated filenames to make
  an answer look sourced. An authentic link still needs to support the claim.

## Uncertainty and questions

A column name or plausible-looking magnitude does not establish physical units or
calibration. Describe unresolved interpretations as uncertain. Ask a focused
question when the missing meaning materially changes the analysis, and continue
independent work. Keep a user's clarification attributable to that user; it does
not independently verify measurements.

State which tables, dates, columns and sample/full-table scope were checked. Give
counts with denominators and explain analytical exclusions. When evidence
conflicts, show the conflict, the approach taken and its limits. Distinguish
source-reported numbers from calculations performed during this work. A null
result can be useful when its scope and evidence are clear.

Workspace notes or a card are optional ways to retain findings and open questions.
Source preservation and evidence quality matter; a particular prose label or
record template does not make a claim true.
