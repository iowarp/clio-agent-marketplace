---
name: work-with-presentations
title: Create and review presentations
description: Create, edit and inspect editable PowerPoint presentations, including slide content, images, notes and rendered layout review.
---

# Work with presentations

`prepare_document_runtime` returns the execution-host commands and library
inventory. `python_argv` runs Python builders (uv selects the prepared Python)
and `javascript.script_argv` runs JavaScript builders (pnpm executes managed
Node); each takes the saved `.py` or `.mjs` builder's path appended to the
argument array. A tool that writes files, or small UTF-8 shell writes (about
1-2 KB per call on Windows), saves a builder. A whole deck builder embedded in
one command, or a single large here-string piped to `Set-Content`, exceeds
launcher limits before it can save the file, even below the shell tool's
advertised input budget, and the same form fails again on retry. A saved builder
stays available for inspection and revision.
`python-pptx` in the prepared Python environment creates slides, as does
`pptxgenjs` when JavaScript is ready. JavaScript builders stored in the returned
JavaScript workspace resolve both CommonJS and ES module imports. A working
Node executable alone does not make packages available to scripts stored elsewhere.
The supplied pnpm command adds task dependencies in a separate task-owned
project, whose manifest and lockfile record them.

`references/slide-design.md` covers narrative, theme and layout decisions for a
new deck. `references/pptxgenjs.md` covers the shipped JavaScript library's
layout units, reusable theme, image sizing and speaker notes example.
`references/python-pptx-editing.md` covers preserving text-run formatting, native
objects and speaker notes in Python edits to an existing deck.
These files load with this skill's returned ID and `file` argument. The guidance
adapts to the user's audience and evidence; the sample is not a finished
presentation.

`examples/create-reference-deck.mjs` is a runnable, fictional six-slide deck
with a shared theme, editable chart and tables, varied layouts and speaker notes.
It loads with the same skill ID and `file` argument and runs from the prepared
JavaScript workspace, where its imports resolve. Its sample data are design
examples, not user findings.

`prepare_document(path, action="inspect")` inspects an existing deck and writes a
content derivative that can be read in bounded sections; a deck over the page
limit takes a range such as `pages="1-10"`. The result includes slide numbers,
shapes, groups, text, table cells, shape bounds and speaker notes. Reading and
rendering a reference shows its dimensions, typography and layout conventions,
which carry into an edit unless the user requests a redesign. Slide order, notes,
hyperlinks, charts and other objects outside the requested edit are part of the
person's deck.

A new deck's slides follow from its intended narrative: what each slide needs the
reader to understand. Native text, charts and tables stay editable; images suit
actual image content, and a whole slide flattened into a picture is no longer
editable. Explicit slide dimensions and font choices, and shared layout
constants, keep slides consistent. A PowerPoint object's declared bounds do not
prove that its text fits; wrapping depends on the renderer and installed fonts.

A new presentation's substance and slide count follow from its audience,
occasion and the supplied evidence. An outline, two-slide sample or empty
placeholder deck does not complete a request for a meeting presentation. Strong
slides have a distinct purpose, a clear title and the actual evidence as the
visual focus: a legible figure, comparison, table or explanation. Source
identifiers, units and caveats belong with findings; speaker notes hold
supporting references and presenter context.

A consistent type and colour system, generous margins and varied compositions
suited to the content read well. Around 30–36 point titles and 18–24 point body
text are useful starting sizes for a widescreen meeting deck. A few readable
points and a meaningful visual communicate more than dense paragraphs or repeated
default bullet layouts. Generic slogans, blank slides and filler added merely to
reach a slide count weaken a deck. The slide overviews show weak composition as
well as clipping or overlap.

In `python-pptx`, a small edit to the relevant text runs keeps their formatting;
assigning `shape.text` or `paragraph.text` rebuilds the runs and can discard
their font, size and colour. The rendered overview shows the changed slide. A
`pptxgenjs` builder creates new decks; it does not provide a general importer for
editing an existing deck. Unsupported objects need scoped OOXML edits or a
preservation-aware tool. Reopening the generated file shows its slide count,
content, notes and objects.

`prepare_document(output_path, action="render")` produces a LibreOffice PDF and
slide PNGs; a long deck renders in explicit page ranges. The render returns
`contact_sheets` with up to six slides in a two-column, three-row grid alongside
full `images`. The sheets show theme and compositional consistency across the
deck. Individual slides, through `view_image` or `view_pdf` when available,
resolve what the overviews leave unclear: text or chart labels too small to
assess, or uncertain overlap, cropping, text fit, contrast or image proportions.
When the overview provides enough evidence, individual slides add nothing. A fix
belongs in the native source, and only a new render shows it. PDF conversion may
differ from PowerPoint, so local rendered review is not acceptance in PowerPoint.

Clio uses bundled LibreOffice or provisions a private verified copy when rendering.
When provisioning fails or the model cannot receive images, the deck has not been
visually reviewed. Successful generation, shape-bound checks and text extraction
do not establish visual quality.
`create_artifact(path=output_path, kind="report", pdf_preview=true)` registers the
requested editable `.pptx` with a version-bound PDF preview for Clio's viewer.
Clio shows a published artifact's card when the final response names it. The
runtime's workspace-file or registered artifact/resource citation format makes
references clickable; browser-local `file://` links are not.
The publication result's `pdf_previews` reports whether each preview was made. A
saved preview is not visual review.
Requested visual review is done once the slide images have actually been
inspected; a failed render leaves it undone, and only the user can waive review
they requested.
A separately registered review PDF does not bind to the editable deck;
`pdf_preview=true` on the source call, or on its batch item, creates that
relationship.
The requested editable deck is the deliverable. PDFs made only for review or
display are derivatives of it; registering one separately lists it as another
deliverable. `used` names the actual source documents or data; the review PDF is
derived from this output, not a source of it.
