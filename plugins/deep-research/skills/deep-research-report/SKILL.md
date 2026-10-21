---
name: deep-research-report
description: The source ledger a deep-research coordinator keeps from the first fetch, and the critic-approved Markdown report artifact it delivers - dispositions, citation coverage, report sections, create_artifact fields and the final chat response.
---

# Deep research report

Load this when deep research starts. The ledger is kept throughout the run; the
report is written only after the critic returns `PASS`.

## Source ledger

Give every attempted fetch one record: requested URL, final fetched URL after
redirects, title, document or source type, author or issuing organization when
known, publication or update date when stated, fetch outcome, and one
disposition:

- `USED_AND_CITED`: fetched content materially informed a claim, comparison,
  conclusion, scenario, or recommendation in the report;
- `READ_NOT_USED`: read as background but did not influence the report;
- `REJECTED`: stale, irrelevant, contradicted, insufficiently authoritative, or
  otherwise deliberately excluded, with the reason;
- `FETCH_FAILED`: not read, with the exact failure.

Every `USED_AND_CITED` source has at least one inline Markdown citation at the
exact claim it supports and appears in the report's references. Never cite
`READ_NOT_USED`, `REJECTED`, `FETCH_FAILED`, a search result, or a page whose
relevant content was not fetched. If fetched content changes the reasoning but
is only indirectly visible in the prose, cite the corresponding inference or
state the influence explicitly. Do not hide a used source merely because another
source supports the same claim.

For a paper, preserve the title, authors or responsible organization, venue or
publisher, publication year or date, and DOI plus the successfully fetched paper
or authoritative landing-page URL when available. Distinguish a paper actually
read from a search snippet, abstract-only page, or inaccessible PDF.

## Search degradation

Treat a search as successful when the configured provider returns enough
relevant results through one or more responsive engines. Do not report an
individual engine's rate limit, CAPTCHA, timeout, or suspension when responsive
engines adequately covered that search; raw tool telemetry remains the audit
record. Surface degradation only when it materially narrowed coverage, removed a
needed source family or perspective, made results unreliable, or caused the
search itself to fail.

## The report

Produce one polished, self-contained Markdown report. It is the primary
deliverable, not an appendix to a chat answer. Write for the user, not as a
process log: lead with the answer or assessment, then the evidence and
reasoning in the clearest structure for the question. Use normal Markdown links
beside the claims they support. Never cite a search-results page, an unfetched
candidate URL, a URL from memory, or a source the critic found mismatched.

Include, adapted to the question:

1. title, research question, scope, evidence as-of date, and concise executive
   answer;
2. methodology and important evidence boundaries;
3. findings and analysis with inline citations on every material sourced claim;
4. clearly labeled synthesis, inferences, scenarios, and recommendations;
5. counterevidence, disagreements, risks, and unresolved uncertainty;
6. conclusion;
7. `References` containing every `USED_AND_CITED` source and no source that was
   not cited inline; and
8. `Source audit` listing every attempted fetch under `USED_AND_CITED`,
   `READ_NOT_USED`, `REJECTED`, or `FETCH_FAILED`, plus only search-provider or
   engine degradation that materially limited coverage. Search queries may be
   summarized here but are never citations.

Citation coverage is semantic, not decorative. Put citations immediately after
the claims they support. A paragraph with several independently sourced claims
needs enough citations to make the mapping unambiguous. Do not place a bare
bibliography at the end while leaving the body unsupported.

Clearly distinguish sourced facts and documented positions; your synthesis or
inference; scenarios, forecasts, and assumptions; and unresolved disagreements,
unavailable pages, and evidence limitations.

## The artifact

Call `create_artifact` with the complete report as inline `content`, a
descriptive `.md` `name` inside the active workspace, `kind="report"`, and an
annotation identifying it as the critic-approved deep-research deliverable. Set
`used` to the exact final fetched URL of every `USED_AND_CITED` source, in
first-use order, plus any workspace path or artifact id that materially informed
the report. Do not put `READ_NOT_USED`, `REJECTED`, `FETCH_FAILED`,
search-result, or remembered URLs in `used`. Use the exact path or artifact
reference the tool returns; never invent, normalize, or reconstruct it. If
creation fails, repair and retry when safe or report a typed deliverable
failure; never claim the research completed without a real artifact.

## The final chat response

Keep it concise: the principal conclusion, the exact report artifact returned by
`create_artifact`, the research and critic status, and material limitations. Do
not paste a second, divergent version of the report into chat. When it cites
external pages directly, format each citation as a standalone list item in this
shape and keep consecutive citations together:

`- Source: [descriptive source title](full URL) — brief relevance or limitation`

Do not use a bare URL or replace the descriptive title with a domain name.
