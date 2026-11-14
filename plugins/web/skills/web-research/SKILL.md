---
name: web-research
title: Research the web with web_search and web_fetch
description: How to find and read web sources well with CLIO's web tools - writing queries, using filters, reading results and their saved full answers, recovering from failed reads, and quoting what a page actually says.
keywords:
- level:L0
- web
---

`web_search` finds candidate pages; `web_fetch` reads one. A search result is a
lead, not evidence: read the page before you rely on anything in it.

## Write the query

- Name the thing precisely, with the terms an authoritative page would use
  (the standard's number, the library's name, the instrument, the agency).
- Put constraints in the filters, not in the query text: `after`/`before` for
  dates (YYYY-MM-DD), `include_domains`/`exclude_domains` for sites, and `kind`
  (`research`, `news`, `pdf`) for the kind of page.
- One idea per query. When results drift, rephrase with vocabulary taken from
  the best result so far, or search for the counter-claim.
- For papers, prefer `literature_search` when the `literature` tools are
  available; use `web_search` for documentation, data portals, agency pages,
  software and grey literature.

## Read the results

Each result has a title, URL, date when known and a short snippet. The
`payload_file` holds everything the search source returned, including longer
excerpts; read it with the file tools before running a near-identical search.

`notes` explain how the answer was produced:

- another source answered because the first was resting or used up;
- `filters_applied_by_clio`: the source could not apply a filter, so CLIO removed
  results outside it. Results without a date stay in, so check dates yourself
  when they matter;
- a source failed or needs the person's attention.

These are facts about the search, not about the topic. Mention them only when
they limit what you could find.

A failed search says why in `error.advice`. A source that did not answer twice in
a row (`search_source_temporarily_down`) has a temporary problem; it does not mean
nothing matches. Call `web_search` again with the same query: the call waits
`retry_after_s` and asks that source again, and if it fails again CLIO moves the
search to `next_source`. Read pages you already found while you wait, if useful.

## Read a page

`web_fetch` returns the page as Markdown in `content`, with the final `url`
after redirects and a `title`. Cite the final URL.

When a read fails:

- try the same document at another address: the publisher's landing page, the
  arXiv `/abs/` or `/html/` page instead of a PDF, a mirror, or the DOI resolver;
- a PDF is saved locally (`pdf_path`); read it with `view_pdf` when you can;
- `reader` shows when a hosted service read the page for CLIO, which may serve a
  cached copy; prefer a fresh read when currency matters.

## Quote what the page says

Copy the exact words from `content` when a claim depends on them, with the
units, populations, dates and qualifications attached. Keep what the source
states separate from what you infer from it.
