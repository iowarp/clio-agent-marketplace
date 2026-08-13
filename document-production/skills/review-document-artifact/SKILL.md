---
name: review-document-artifact
description: Apply a CLIO artifact_review instruction to the exact Markdown, PDF-backed source, LaTeX, HTML, OOXML, or OpenDocument version and create a new immutable artifact revision. Use when the turn contains an artifact_review part, a selected quote/region/cell/shape, or a native @clio comment.
---

# Review Document Artifact

1. Read the `artifact_review` fields before editing: `artifact_id`, version, SHA-256, anchor, and comment.
2. Resolve the canonical editable source. PDF is a rendition unless it is itself the source; follow recorded source lineage and do not reverse-engineer a PDF when source exists.
3. Verify the selected version/hash is still the intended base. If the head advanced, stop and report a stale anchor instead of applying the anchor elsewhere.
4. Load the format skill: `$edit-markdown-html`, `$author-latex-pdf`, `$edit-ooxml-word`, `$edit-ooxml-spreadsheet`, `$edit-ooxml-presentation`, or `$edit-opendocument`.
5. Make the smallest change satisfying the comment. Preserve unrelated content, styles, formulas, media, accessibility metadata, native comments, and unsupported package parts.
6. Validate the real output in its native format and, when available, its rendered rendition.
7. Save the canonical file. CLIO’s artifact change feed mints the new immutable revision; cite the new version and explain any blocked compatibility risk.

Read [anchor-semantics.md](references/anchor-semantics.md) when resolving anything other than a plain text quote.
