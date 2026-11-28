---
name: evidence-and-claims
title: Evidence and Claims
description: Use when writing findings or reports that explain what sources say, what the analysis checked and what remains uncertain, with clickable supporting references.
keywords:
- level:L0
- provenance
- uncertainty
---

# Evidence and claims

An answer is easy to read and inspect when its evidence is explained in ordinary
sentences. Bracketed status labels on every claim, or a generic source list
appended to every paragraph, make it harder to read.

- **Source documentation:** "The protocol describes this measurement as projected
  area." A link to the inspected protocol and its relevant section supports it. Documentation
  can be stale or wrong; distinguish its description from an independent check.
- **Data checks:** "I counted the distinct sample identifiers in the inspected table." The
  actual table, the key/count calculation and the relevant recorded output
  support it. A sampled check supports a statement about the sample, not the full table.
- **Interpretation:** "This suggests a measurement ceiling, but calibration is
  still needed to distinguish it from a biological plateau." Its support is the evidence,
  the competing explanation and what would resolve the uncertainty.

A short citation at the end of the supported sentence or paragraph is fine.
A meaningful clickable label reads best, such as the protocol name or measurement
table, using the file/reference link format supplied by CLIO. A citation
works when it is an actual inspected file's precise path or a returned
artifact/resource reference; a guessed filename leads nowhere. Bare backticked
names are not clickable citations. A source that cannot be opened through the
available reference mechanism is not openable by the reader either, and a
fabricated link misleads.

## Match the evidence to the claim

- A manifest can support export identity or a declared file list. A README can
  support a documented definition. Neither establishes actual row counts,
  calibration, data quality, a computed effect or successful onboarding.
- A computed result is supported by the relevant table, columns and calculation,
  with source references, relevant input/output versions and the actual result used.
  A saved analysis report can help when its evidence and assumptions were checked.
- A `card.py status` receipt describes a saved record's status. It does not verify
  a scientific finding. "Audit in progress" is a progress update, not a source.
  An ended child turn also does not establish that its assignment succeeded.
- A completed audit is evidence through its actual findings and supporting
  references and their underlying sources, not through the mere existence of an
  audit task. Repeating selected calculations checks it.
- A document that was not inspected, or an unrelated filename, does not source an
  answer. An authentic link still needs to support the claim.

## Uncertainty and questions

A column name or plausible-looking magnitude does not establish physical units or
calibration. Unresolved interpretations are uncertain. A focused question to the person
resolves a missing meaning that materially changes the analysis; independent work
does not depend on it. A person's clarification is attributable to them; it does
not independently verify measurements.

A claim's scope is the tables, dates, columns and sample/full-table extent that
were checked. Counts mean more with denominators, and analytical exclusions with
their reasons. Conflicting evidence, the approach taken and its limits are part of
the result. Source-reported numbers and calculations performed during this work
are different kinds of evidence. A null
result can be useful when its scope and evidence are clear.

Workspace notes or a card are optional ways to retain findings and open questions.
Source preservation and evidence quality matter; a particular prose label or
record template does not make a claim true.
