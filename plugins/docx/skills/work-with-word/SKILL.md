---
name: work-with-word
title: Read, create and review Word documents
description: Create, edit and inspect Word documents and templates, preserving existing formatting and checking rendered pages.
---

# Work with Word documents

`prepare_document_runtime` returns this session's paths, packages, fonts and
execution-host facts, with a prepared `python_argv` command. A Python project
may select a different environment when using `uv run`. For JavaScript creation,
`docx` is available when the returned JavaScript status is ready; an importing
script in the returned JavaScript workspace resolves it and runs with the
returned `javascript.script_argv` (pnpm executes managed Node).

`references/report-design.md` covers content and layout decisions for a new
report, or for adding or reflowing report sections. `references/python-docx-editing.md`
covers style reuse and section insertion in Python template edits.
`references/docx-js.md` covers the shipped JavaScript library's units, styles,
page fields and native table example. These files load with this skill's returned
ID and `file` argument; they are supporting guidance, not a required template or
a substitute for the user's evidence.

`examples/create-reference-report.mjs` is a runnable, fictional two-page report
with a chart, native table, headings and page numbers. It loads with the same
skill ID and `file` argument and runs from the prepared JavaScript workspace;
its sample data demonstrate composition, not user findings. A whole report
builder embedded in one shell command exceeds launcher limits; a builder saved
to a workspace file runs with a short command.

`prepare_document(path, action="inspect")` on an existing `.docx` writes a
content derivative of its body paragraphs and tables in order, readable through
bounded file reads. It does not establish pagination, floating-object placement,
revision handling, comments, or header/footer layout; a render shows those.
Uploaded attachments have workspace working copies at the supplied copy path;
the original stays untouched.

`python-docx` in the prepared interpreter creates and edits documents. Styles
and native headings, lists and tables keep the result editable. A template's
section dimensions and existing styles are visible by inspection. Imported
documents may use custom heading and table styles: the actual style objects from
comparable content work where an assumed built-in name may not exist or match.
A new section's heading and content belong together in document order. Page
size, margins and table widths are explicit settings. Assigning paragraph text
replaces its runs; replacing text in individual runs keeps their formatting.
Images, hyperlinks and fields outside the task are part of the person's document;
an existing document recreated from extracted text loses them.

A new report's content comes from the supplied evidence: its reader, purpose,
main conclusion and source limitations, with length set by the material and the
user's intended use. A report needs connected explanation, supported findings
and useful figures or tables where the evidence calls for them. A short sample,
outline or placeholder is not a completed report. Results invented to fill pages
are fabrication.

A well-set report has a coherent heading hierarchy, readable body text around
11–12 points, deliberate paragraph spacing, and page numbers when it runs to
several pages. Figure captions stay with their figures, images keep their
proportions, and source images have enough detail. Quantitative evidence carries
its units and source identifiers. Table headers repeat across pages; isolated
headings and large accidental blank gaps are layout defects. A restrained report
gets its visual quality from typography, alignment and clear evidence rather
than decorative boxes.

`python-docx` does not provide every OOXML feature. Tracked changes, complex
fields, native comments and unsupported objects live in the package XML and
relationships, where `lxml` or `defusedxml` make scoped changes. A successful
library save does not show that revisions or comments survived. Legacy `.doc`
files need an explicit LibreOffice conversion to a new `.docx`, which can affect
fidelity.

Output written to a new workspace file leaves the source unchanged; reopening it
shows the text, tables, sections and images.
`prepare_document(output_path, action="render")` needs LibreOffice on the
execution host; Clio uses its bundled renderer or provisions a private verified
copy automatically. The runtime inventory reports its status and accepts
`CLIO_DOCUMENT_SOFFICE` for an installed portable executable. Rendering uses a
fresh profile and produces a separate PDF and page PNGs.

The render returns both full page `images` and labelled `contact_sheets` with up
to six pages in a two-column, three-row grid. The sheets show consistency and
pagination across the document. Individual pages, through `view_image` or
`view_pdf` when exposed, resolve what the overviews leave unclear: small or
unclear text, figure labels, suspected table splits, wrapping, glyphs or
header/footer problems. When the overview provides enough evidence, individual
pages add nothing. A fix belongs in the native source, and only a new rendition
shows it. Extraction and rendering are distinct from visual review. Without
conversion or visual tools, the layout is unverified; the editable source remains
the deliverable.

`create_artifact(path=output_path, kind="report", pdf_preview=true)` designates
the final editable artifact with a version-bound PDF preview. The UI
requires this source-bound preview to open the Word artifact directly. A PDF from
`prepare_document` is a review derivative; separately registering that PDF does
not bind it to the editable artifact. In a batch, `pdf_preview=true` applies per
editable Office item. Clio's UI
opens the saved PDF when the source artifact is selected; users can still download
or edit the original. `pdf_previews` reports conversion failures. A preview is
not visual review. Clio shows a published artifact's card when the final response
names it. The runtime's workspace-file or registered artifact/resource citation
format makes references clickable; browser-local `file://` links are not.
The requested editable document is the deliverable. PDFs made only for review or
display are derivatives of it; registering one separately lists it as another
deliverable. `used` names the actual source documents or data; the review PDF is
derived from this output, not a source of it. Supplied sources are citable;
assumptions introduced while drafting are not the user's content.
