---
name: literature-search
title: Find and follow scholarly works with literature_search and literature_lookup
description: How to search scholarly sources well with CLIO's literature tools - keyword queries, field and kind, reading merged results, following references and citations, telling preprints from published versions, and reaching readable text.
keywords:
- level:L0
- literature
---

`literature_search` asks several scholarly sources at once and merges the works
they return. `literature_lookup` opens one work: its metadata, where to read
it, what it cites, what cites it, and its other versions. `web_fetch` on a work's
`readable_url` reads its text.

## Search

- The sources match keywords, not questions: the main terms of the topic and
  their common synonyms. Distinct vocabularies match better as separate searches
  than as one long query.
- `field="any"` (the default) asks every broad source: OpenAlex, Crossref,
  arXiv, ChemRxiv, Europe PMC, OSTI.gov and DataCite. Another `field` narrows a
  search to one area's sources; `field="chemistry"` adds ChemRxiv preprints.
- bioRxiv and medRxiv preprints arrive through Europe PMC (`field="life"`).
- A source missing from the results is named in `notes` with what happened and
  what to do; the other sources' works are complete.
- `kind` set to `preprint`, `review` or `dataset` restricts the works to that
  kind; `after`/`before` bound the publication date.
- `found_in` lists the sources that returned a work. Several sources agreeing
  is a sign of a well-indexed work, not of quality.
- `payload_file` holds every work found with full abstracts, often already
  covering what a similar query would return.

## Follow

- `literature_lookup` takes a DOI, arXiv id, `pmid:` or OpenAlex `W` id.
- References lead backward to the foundations of a result and `cited_by`
  forward to replications, corrections and later work. A highly cited paper's
  recent citers often say whether its claim still holds.
- `versions` links a preprint to its published version. A citation names the
  version actually read; when both exist, the published one may have changed
  the claim.

## Read

- An arXiv `readable_url` is the abstract page; the full text is usually at
  `https://arxiv.org/html/<id>`, and the PDF at `/pdf/<id>`.
- When the readable URL is the DOI resolver and the publisher page is
  paywalled, an open copy may exist: the preprint, a repository version, or the
  author's page.
- What was actually read for each work — full text, abstract only, or metadata
  only — bounds what it supports. An abstract supports a claim only as far as it
  states it.
