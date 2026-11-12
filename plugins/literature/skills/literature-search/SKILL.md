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
it, what it cites, what cites it, and its other versions. Read a work's text
with `web_fetch` on its `readable_url`.

## Search

- Write keywords, not questions: the main terms of the topic and their common
  synonyms. Run separate searches for distinct vocabularies rather than one
  long query.
- Set `field` when the topic sits in one area; it adds the sources that cover
  it. Leave it `any` for cross-disciplinary topics.
- Set `kind` to `preprint`, `review` or `dataset` when that is what you need;
  `after`/`before` bound the publication date.
- `found_in` lists the sources that returned a work. Several sources agreeing
  is a sign of a well-indexed work, not of quality.
- `payload_file` holds every work found with full abstracts; read it before
  searching again with a similar query.

## Follow

- Use `literature_lookup` with a DOI, arXiv id, `pmid:` or OpenAlex `W` id.
- Follow references backward for the foundations of a result and `cited_by`
  forward for replications, corrections and later work. A highly cited paper's
  recent citers often say whether its claim still holds.
- `versions` links a preprint to its published version. Cite the version you
  actually read; when both exist, check whether the published one changed
  the claim.

## Read

- An arXiv `readable_url` is the abstract page; the full text is usually at
  `https://arxiv.org/html/<id>`, and the PDF at `/pdf/<id>`.
- When the readable URL is the DOI resolver and the publisher page is
  paywalled, look for an open copy: the preprint, a repository version, or the
  author's page.
- Record what you actually read for each work: full text, abstract only, or
  metadata only. An abstract supports a claim only as far as it states it.
