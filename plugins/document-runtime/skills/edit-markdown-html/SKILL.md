---
name: edit-markdown-html
description: Use to create or revise Markdown (.md, .markdown) or static HTML (.html, .htm) document artifacts, preserving structure, links, accessibility and review anchors.
---

# Edit Markdown and Static HTML

- A selected region belongs to an exact artifact version, and the whole source gives its context.
- Heading hierarchy, link targets, alt text, table headers, IDs used by review anchors, and frontmatter keys outside the request are part of the document.
- A static HTML artifact carries no scripts, inline event handlers, active forms, remote execution dependencies, or navigation tricks. Interaction is a Live Web artifact, which goes through its normal consent.
- Semantic HTML carries structure that presentational containers do not. Print styles keep the PDF rendition legible.
- Markdown structure and HTML parsing are checkable, as are links and assets that resolve locally.
- A save of the canonical source becomes CLIO's new artifact version.
- `create_artifact(..., pdf_preview=true)` gives a new Markdown or HTML deliverable a print preview: the PDF is bound to that version and kept in lineage, not listed as another deliverable. In a batch, each item's `pdf_preview` overrides the call's default.

See [document-quality.md](references/document-quality.md) for completion checks.
