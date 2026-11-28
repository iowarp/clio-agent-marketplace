---
name: work-with-pdfs
title: Read, create and review PDF documents
description: Read, create, edit and verify PDFs through bounded text extraction, structured conversion and rendered-page evidence.
---

# Work with PDFs

This skill covers reading, reviewing, comparing and using PDFs as evidence.
Extracted text is not evidence about layout, figures, equations, scans, or
handwriting.

## Native PDF reading

If the `view_pdf` tool is available, the connected model can read PDFs
natively. Called with the workspace path, it attaches the document to the next
model step; both its text and page images reach the model directly, with no
conversion step. The `pages` argument (e.g. `"1-50"`) reads a page range; a
whole-document call past the configured page ceiling is refused and reports
the document's page count so a range can be chosen.

Without `view_pdf`, the active model has no evidenced native PDF capability;
the conversion, rendered-page and `view_image` path in the rest of this skill
covers that case.

When a provider refuses a native PDF attachment, its successful preparation
does not mean the model read it. The refusal carries a recovery note, and the
same attachment is refused again. Bounded extraction and rendered-page
inspection below work on the same source path and page range.

## Resolve evidence, not accessibility

Every PDF supplied to the turn has a usable path on the connected agent:

- A workspace `@` reference supplies its verified workspace path and revision.
- An uploaded attachment supplies an independent working copy beneath the
  active workspace's `.clio/inputs/` directory. Its immutable custody original
  remains available to CLIO's conversion pipeline.

The supplied workspace path works with shell, Docling, Poppler, OCR, Python,
and other file-based tools. The private custody original is immutable and
belongs to CLIO's conversion pipeline. Every supplied PDF already has a
workspace path, so its accessibility is not in question and a re-upload adds
no new path.

An uploaded attachment has a resource record that may carry a structured
conversion. While conversion is queued or processing, `workspace_resource_wait`
with the supplied task id waits for it. A complete conversion is read through
`workspace_resource_structure`, `workspace_resource_search`, and bounded
`workspace_resource_read` calls for searchable text, tables, and document
structure.

For either source, the workspace path and local tools cover the cases where no
usable conversion exists or the question depends on geometry, layout, figures,
equations, scans, handwriting, or other visual evidence.

## Local conversion and page rendering

`prepare_document_runtime` returns the execution host's verified commands,
packages, fonts and output directory. It uses locked dependencies outside Clio's
own Python environment. Its returned `.tmp/` directory is scratch space for
intermediate scripts and data; source files and requested outputs live in the
active workspace. `prepare_document(path, action="inspect", pages="1-10")`
returns bounded embedded text, and `prepare_document(path, action="render",
pages="1-5")` bounded page PNGs, each with a manifest and content derivative.
Long documents require an explicit range; scans with empty embedded text carry
their content only in the page images, reached by visual inspection or OCR.
Rendering alone does not read an image for the model.

The returned `python_argv` runs authoring and editing scripts (uv selects the
prepared Python). The prepared ReportLab environment creates PDFs; `pypdf` and
PyMuPDF merge, split and rotate pages. Written to a new path, the output leaves
the source intact; reopening it shows its page count and content, and rendered
pages show its layout. `create_artifact` designates the requested final file. A
successful rewrite does not show that forms, signatures or accessibility survived.
Clio shows a published artifact's card when the final response names it. The
runtime's workspace-file or registered artifact/resource citation format makes
references clickable; browser-local `file://` links are not.

When Docling's richer structural conversion is needed and the attachment has no
usable structured derivative, the following existing helper remains available.
Docling is a separate optional dependency and may download model assets; it is
not advertised by the prepared stack unless installed there.

In the commands below, `SKILL_ROOT` is this skill's directory, and `UV` and
`PYTHON` are the absolute `uv` and `python` paths the runtime returned:

```text
"UV" run --no-project --python "PYTHON" --with "docling>=2.0" --with "pymupdf>=1.24" python "SKILL_ROOT/scripts/prepare_pdf.py" "INPUT.pdf" "OUTPUT_DIR"
```

This uses uv's shared cached environment; nothing is installed into the skill
or plugin directory.

`--visual-only` skips the slower text conversion and only renders pages, which
suits a drawing, scan, or other explicitly visual question:

```text
"UV" run --no-project --python "PYTHON" python "SKILL_ROOT/scripts/prepare_pdf.py" "INPUT.pdf" "OUTPUT_DIR" --visual-only
```

The helper performs two independent operations:

- Docling exports Markdown plus its structured JSON document.
- PyMuPDF renders bounded page PNGs and writes a manifest recording every
  output and any partial failure.

`--max-pages`, `--max-bytes`, and `--dpi` bound large documents; the default
limits are intentionally conservative. `manifest.json` records whether each
conversion succeeded.

The Markdown/JSON outputs carry text, headings, tables, and document structure.
A large conversion can be searched and read in relevant sections; read whole,
it fills the model context.

## Visual evidence boundary

An image-capable CLIO model has a `view_image` tool. The Markdown/JSON
conversion is enough when it answers the question faithfully. When converted text is missing or
insufficient—for example, scans, plots, equations, handwriting, or
layout-dependent questions—`view_image` on the relevant rendered page PNGs
attaches the verified workspace image pixels to the next model step; a
successful shell render alone does not count as visual inspection.

Without `view_image`, the active model has no evidenced image capability, and
the evidence is what text, OCR and structured conversion provide. Filenames,
dimensions, metadata and a successful render are not visual facts, and
reattached pages do not give the model an image path it lacks.

For scanned or image-only PDFs, a weak or empty text conversion signals that the
content is in the rendered pages. In a mixed PDF, only the pages whose layout or
figures matter need visual inspection alongside the textual evidence.

## Engineering drawings and diagrams

Questions about dimensions, feature counts, geometry, callout-to-feature
associations, or relative size are always layout-dependent, even when text
extraction contains the requested number. Extracted labels without their
positions do not show which feature they dimension; the page pixels from
`view_image` do. A completed render is not evidence until `view_image` has
returned the page pixels to the model.

Drawing units are not given by decimal style, likely engineering convention,
software metadata, filename, or the magnitude of dimensions. They are known only
when a visible note, title-block field, or explicit callout states them; with no
stated unit, the numerical dimensions are unitless.

On large-format drawings or small, dense callouts, a full-page preview can leave
labels illegible; high-resolution crops of each relevant view or callout region
make them readable. A list of dimensions or radii is complete only as far as its
labels were legible.

## Evidence and completion

- Page numbers and section/table/figure labels, when the source exposes them,
  make claims checkable.
- Source text, observed visual content, OCR output, and inference are different
  kinds of evidence.
- A PDF is fully reviewed when the relevant textual content and every visually
  material page have been checked through a representation the model actually
  received.
- Derivatives go to a separate output directory; the original PDF stays
  unchanged.
