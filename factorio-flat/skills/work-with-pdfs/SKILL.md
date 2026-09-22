---
name: work-with-pdfs
title: Inspect PDFs Through Their Best Available Representation
description: Read and verify PDFs by preferring an existing CLIO structured conversion, then using a bounded local Docling conversion, and rendering pages for genuine visual inspection when text extraction is insufficient.
---

# Work with PDFs

Use this skill when a PDF must be read, reviewed, compared, or used as evidence.
Do not treat extracted text as evidence about layout, figures, equations, scans,
or handwriting.

## Choose the source path

1. For a CLIO attachment, start with `workspace_resource_inspect` using the
   resource id supplied with the turn.
   - If the original PDF is included natively in the current model input, read
     it directly. Use the structured derivative too when its outline, tables,
     or searchable text would make the answer more reliable.
   - If conversion is queued or processing, call `workspace_resource_wait`
     once with the supplied task id. Do not repeatedly poll.
   - If conversion is complete, discover derivative ids with
     `workspace_resource_inspect`, then use `workspace_resource_structure`,
     `workspace_resource_search`, and bounded `workspace_resource_read` calls.
   - Never pass a private resource-custody path to shell or filesystem tools.
     Run the local workflow only when CLIO or the user supplies an accessible
     workspace path for the PDF.
2. For a PDF already in the active workspace, or an attachment materialized to
   an accessible workspace path, use the local workflow below when no usable
   conversion exists or when the conversion is inadequate.

## Local conversion and page rendering

Resolve this skill's directory as `SKILL_ROOT`, then run:

```text
uv run --project "SKILL_ROOT" python "SKILL_ROOT/scripts/prepare_pdf.py" "INPUT.pdf" "OUTPUT_DIR"
```

The helper performs two independent operations:

- Docling exports Markdown plus its structured JSON document.
- PyMuPDF renders bounded page PNGs and writes a manifest recording every
  output and any partial failure.

Use `--max-pages`, `--max-bytes`, and `--dpi` to keep large documents bounded.
The default limits are intentionally conservative. Read `manifest.json` before
claiming either conversion succeeded.

Prefer the Markdown/JSON outputs for text, headings, tables, and document
structure. Search or read only the relevant sections instead of putting an
entire large conversion into the model context.

## Visual evidence boundary

An image-capable CLIO model has a `view_image` tool. Prefer the Markdown/JSON
conversion when it answers the question faithfully. When converted text is
missing or insufficient—for example, scans, plots, equations, handwriting, or
layout-dependent questions—render the relevant PDF pages with the helper and
call `view_image` on each relevant page PNG. That tool attaches the verified
workspace image pixels to the next model step; a successful shell render alone
does not count as visual inspection.

If `view_image` is absent, the active model has no evidenced image capability.
Use only available text/OCR/structured evidence and state the limitation. Never
infer visual facts from filenames, dimensions, metadata, or successful
rendering alone, and do not ask the user to reattach pages merely to compensate
for a missing agent-side image inspection path.

For scanned or image-only PDFs, treat a weak or empty text conversion as a
signal to use the rendered-page path. For mixed PDFs, combine bounded textual
evidence with visual inspection of only the pages whose layout or figures
matter.

## Evidence and completion

- Cite page numbers and section/table/figure labels when the source exposes
  them.
- Separate source text, observed visual content, OCR output, and inference.
- Do not call a PDF fully reviewed until the relevant textual content and every
  visually material page have been checked through a representation the model
  actually received.
- Preserve the original PDF. Write derivatives to a separate output directory.
