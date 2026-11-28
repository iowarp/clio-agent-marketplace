---
name: paper-search
title: Search Scientific Literature for Relevant Sources
description: Decompose a literature question into search lanes, fetch and read actual sources, and return only what was verified from the fetched text.
keywords:
- level:L0
- scientific-method
---

A question has a decision it informs, and a relevant paper may use any of
several terms and synonyms: a single search term misses adjacent literatures
that use different vocabulary for the same concept. A broad question splits
into independent lanes (mechanism, measurement method, competing approach,
material system) that can be searched without duplicating each other.

The `literature` tools search scholarly sources (`literature_search`) and
follow a work (`literature_lookup`); the `literature-search` skill covers their
use. Web search reaches grey literature, documentation and data portals.

A search-result snippet or title is not evidence of what a paper found; only
the fetched and read source is citable. Per source, what was read (full text
vs. abstract only), publication venue and date, and the specific claim it
supports or contradicts are what make it usable.

Consequential references lead forward and backward: a cited method or a paper
that cites the one just found often matters more than the next search result.
A search is done when additional searches stop changing the claim map, not at
a fixed count. Synthesis of the set is `literature-review`.
