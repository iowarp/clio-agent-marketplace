---
name: review-document-artifact
description: Use when the turn carries comments on an artifact or a workspace file (a "Review of ..." block with marks S1, S2, ...), or a native @clio comment, to apply them to that exact version as a new revision.
---

# Review Document Artifact

The person marked parts of one version and wrote a comment on each mark. You
receive one readable block per send:

- A header naming the artifact, its version and SHA-256, and what to edit: the
  source when they marked a PDF rendition, or the producing script ("Produced
  by ...") when a tool call made the file. "Producer unknown" means no recorded
  call made it.
- "Image 1 is ..." lines for the labelled overview of each marked page, followed
  by one crop per mark at twice its size, in label order.
- One entry per mark, `S1 (region, attached as image 2)`, with the lines that
  apply: Box, Element, Selected, Before, After, Under, Source, Picture, Made by,
  Note and Comment.

The comment is the instruction; the other lines say where it points, and the
overview and crops show what was marked.

- The header and the Source, Picture and Made by lines name what to edit. A PDF
  is a rendition unless it is itself the source; a PDF or image reverse-engineered
  when the source or the script exists diverges from them.
- The format skills, loaded with `load_skill`, are `edit-markdown-html`,
  `author-latex-pdf`, `edit-ooxml-word`, `edit-ooxml-spreadsheet`,
  `edit-ooxml-presentation` and `edit-opendocument`.
- Unrelated content, styles, formulas, media, accessibility metadata, native
  comments and package parts the edit does not understand are part of the file.
- The native format and, when available, its rendition show whether the output is
  right. A figure made by a script changes when the script reruns, and the new
  image shows the result.
- A save to the same file becomes the artifact's next version, which CLIO links
  from each comment.
- CLIO stores the final answer as the reply on every comment of the send, so the
  person reads there what changed for S1, S2, and so on, and which marks could not
  be applied.

A `Note:` line is a typed reason that part of a mark could not be resolved, such
as `quote_not_found` or `source_unmapped`. The rest of the entry still holds; the
note marks what it left open.

[anchor-semantics.md](references/anchor-semantics.md) covers what each line
means and comments on figures, pages, HTML and native comments.
