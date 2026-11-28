---
name: create-pdf-report
title: Create a PDF Report
description: Create a polished PDF report as a PDF deliverable, built with ReportLab and checked page by page. CLIO's ordinary reports are Markdown.
keywords:
- level:L0
- report
- pdf
---

# Create a PDF Report

This skill builds a PDF deliverable. CLIO's ordinary reports are Markdown; a PDF
is the format when the person asks for one.

## Build from grounded content

Page layout depends on the report's claims, data, citations, and intended
audience. Units, uncertainty, provenance, and the distinctions between supplied
facts, observed results, and inference are part of that content. Specificity the
evidence does not support is decoration, not content.

ReportLab generates the PDF directly. Flowable layout absorbs changes in text and
page count; fixed coordinates suit short, deliberately composed layouts. A
builder and temporary assets kept outside the final output directory stay out of
the deliverable, and source assets stay unchanged.

Supplied figures are evidence. A generated image is not, and its label says it
was generated.

## Verify the artifact

Each meaningful layout change can introduce new defects. The checks:

- `pypdf` reopens the PDF and shows page count, expected content, and document
  metadata.
- Poppler renders every page to PNG.
- `view_image` on the rendered pages shows clipping, overlap, unreadable text,
  poor spacing, broken glyphs, misplaced figures, and weak page transitions.
  Content extraction alone is not evidence of visual correctness.

A page `view_image` did not show the model, because it failed or reported that
the image was not shown, has not been visually checked.

`uv` runs Python and manages dependencies. Typical dependencies are `reportlab`,
`pypdf`, and Pillow.
The PDF goes where the person asked for it, under the name they gave, or else
where the workspace's own output convention puts outputs. Intermediate renders
belong in the session's scratch folder, not the workspace.
