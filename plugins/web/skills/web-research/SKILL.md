---
name: web-research
title: Research the web with web_search and web_fetch
description: How to find and read web sources well with CLIO's web tools - writing queries, using filters, reading results and their saved full answers, recovering from failed reads, and quoting what a page actually says.
keywords:
- level:L0
- web
---

`web_search` finds candidate pages; `web_fetch` reads one. A search result is a
lead, not evidence: what a page says is in the page, not the snippet.

## Writing the query

- Precise names, with the terms an authoritative page would use (the
  standard's number, the library's name, the instrument, the agency), find
  better results.
- The filters carry constraints more reliably than query text: `after`/`before`
  for dates (YYYY-MM-DD), `include_domains`/`exclude_domains` for sites, and
  `kind` (`research`, `news`, `pdf`) for the kind of page.
- A query with one idea returns focused results. Vocabulary taken from the best
  result so far, or a search for the counter-claim, helps when results drift.
- For papers, `literature_search` (when the `literature` tools are available)
  searches scholarly sources; `web_search` covers documentation, data portals,
  agency pages, software and grey literature.

## Reading the results

Each result has a title, URL, date when known and a short snippet. The
`payload_file` holds everything the search source returned, including longer
excerpts, readable with the file tools; a near-identical search usually returns
the same thing.

`notes` explain how the answer was produced:

- another source answered because the first was resting or used up;
- `filters_applied_by_clio`: the source could not apply a filter, so CLIO removed
  results outside it. Results without a date stay in, so their dates are
  unchecked;
- a source failed or needs the person's attention.

These are facts about the search, not about the topic; they matter to the
person when they limit what could be found.

A failed search says why in `error.advice`. A source that did not answer twice in
a row (`search_source_temporarily_down`) has a temporary problem; it does not mean
nothing matches. Calling `web_search` again with the same query waits
`retry_after_s` and asks that source again, and if it fails again CLIO moves the
search to `next_source`. Pages already found stay readable meanwhile.

## Reading a page

`web_fetch` returns the page as Markdown in `content`, with the final `url`
after redirects and a `title`. The final URL is the one that resolves for a
reader.

When a read fails:

- the same document is often at another address: the publisher's landing page,
  the arXiv `/abs/` or `/html/` page instead of a PDF, a mirror, or the DOI
  resolver;
- a PDF is saved locally (`pdf_path`), which `view_pdf` can read;
- `reader` shows when a hosted service read the page for CLIO, which may serve a
  cached copy; a fresh read matters when currency does.

## What the page says

A claim that depends on exact words is checkable when quoted from `content`,
with the units, populations, dates and qualifications attached. What the source
states and what is inferred from it are different kinds of evidence.
