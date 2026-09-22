---
name: create-pdf-report
description: Create a polished PDF report when the scientist explicitly requests a PDF deliverable. Ordinary reports remain Markdown unless another format is requested.
---

# Create a PDF Report

Load this skill only when the scientist asks for a PDF report or another PDF
deliverable. A request for a report without a requested file format should
produce Markdown, not a PDF.

## Build from grounded content

Establish the report's claims, data, citations, and intended audience before
laying out pages. Preserve units, uncertainty, provenance, and distinctions
between supplied facts, observed results, and inference. Do not add decorative
specificity that the evidence does not support.

Generate the PDF directly with ReportLab. Prefer flowable layout for reports
whose text or page count may change; use fixed coordinates only for short,
deliberately composed layouts. Keep the builder and temporary assets outside
the final output directory, and preserve source assets.

If the report benefits from illustrations, use supplied figures first. Create
new images only when the scientist requests them or they materially improve
the deliverable, and label generated images honestly.

## Verify the artifact

After each meaningful layout change:

1. Reopen the PDF with `pypdf` and verify page count, expected content, and
   document metadata.
2. Render every page to PNG with Poppler.
3. Inspect every rendered page with `view_image` for clipping, overlap,
   unreadable text, poor spacing, broken glyphs, misplaced figures, and weak
   page transitions.
4. Correct defects and repeat the checks. Content extraction alone is not
   evidence of visual correctness.

Use `uv` for Python execution and dependency management. Typical dependencies
are `reportlab`, `pypdf`, and Pillow; use only the packages the report needs.
Place final deliverables under `output/pdf/` when the workspace has no more
specific output convention, and keep intermediate renders under `tmp/pdfs/`.

Deliver the final PDF only after both logical and visual verification pass.
