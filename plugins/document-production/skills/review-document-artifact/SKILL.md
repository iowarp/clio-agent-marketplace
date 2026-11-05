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

1. Read every entry and look at the overview and crops before editing. The
   comment is the instruction; the other lines say where it points.
2. Edit what the header and the Source, Picture and Made by lines name. A PDF is
   a rendition unless it is itself the source. Do not reverse-engineer a PDF or
   an image when the source or the script exists.
3. Load the format skill with `load_skill`: `edit-markdown-html`,
   `author-latex-pdf`, `edit-ooxml-word`, `edit-ooxml-spreadsheet`,
   `edit-ooxml-presentation` or `edit-opendocument`.
4. Make the smallest change that satisfies each comment. Preserve unrelated
   content, styles, formulas, media, accessibility metadata, native comments and
   package parts you do not understand.
5. Validate the output in its native format and, when available, its rendition.
   When a script made the figure, rerun it and look at the new image.
6. Save the same file. CLIO records the saved file as the artifact's next
   version and links it from each comment.
7. Answer by label: what you changed for S1, S2, and so on, and why. CLIO stores
   your final answer as the reply on every comment of the send, so say plainly
   which marks you could not apply.

A `Note:` line is a typed reason that part of a mark could not be resolved, such
as `quote_not_found` or `source_unmapped`. Act on what the entry does establish,
and say what the note left open instead of guessing.

Read [anchor-semantics.md](references/anchor-semantics.md) for what each line
means and for comments on figures, pages, HTML and native comments.
