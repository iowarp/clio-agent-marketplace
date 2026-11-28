# Presentation design

## A narrative that fits the occasion

The narrative follows from the audience, meeting purpose and time available: the
principal takeaway, and what the audience needs to understand to assess it. Each
slide then has a purpose and a descriptive title. A research meeting might need
context, data and method, several findings, uncertainty and a decision; a fixed
slide count or a two-slide test deck is not a narrative.

The content is the supplied evidence. Units, identifiers and exclusions belong
next to quantitative findings. Notes suit detailed references and presenter
context; a caveat that changes the conclusion belongs on the slide. Results,
quotations or decorative metrics invented to fill a layout are fabrication.

Each comparison has its own population. A median across all observations on
each date and a median change among paired subjects are different summaries;
shown together, they can look as if they came from the same sample.

## One visual system

An edit inherits the reference deck's conventions. A new deck's system is an
explicit aspect ratio, fonts available on the execution host, a neutral base,
one primary accent and consistent margins. Around 30–36 pt titles and 18–24 pt
body text suit a widescreen meeting deck. Source captions can be smaller while still
readable at the intended viewing size.

Theme defaults or shared builder constants keep typography coherent. Aligned
title positions, figure edges and footers, and content with room to breathe on a
slide that is not mostly empty, read as designed. Design quality comes from
hierarchy, composition and meaningful evidence, not repeated rounded cards or
decoration. Rendered theme effects can differ from assigned colours: some
libraries inherit shadows or bevels from the default Office theme even when a
builder only sets fill and line properties, so a plain shape declaration can
still render with them.

## Layout follows the content

- A finding with one main figure: a large, legible figure and a short
  interpretation, with the figure's aspect ratio and units kept.
- A comparison: two views aligned on the same scale, or an editable table or
  chart, with colour meaning consistent across slides.
- A method or sequence: a concise numbered explanation, or a clear diagram
  when it communicates an actual relationship.
- An uncertainty or decision: what is known, what is unresolved and how that
  affects the next action.

Composition can vary with the content; not every slide is a title and a default
bullet list. Dense material splits across meaningful slides. Small-multiple
charts often have panel labels that are unreadable at meeting scale; separate
panels, or a figure regenerated from the provided data, can fix that while the
complete underlying evidence stays and any change in grouping or exclusions is
explained.

Titles, narrative text, tables and charts stay editable as native objects; source
figures can be images. A whole slide rendered into a picture hides its layout
problems rather than fixing them.

## What the audience sees

Reopening the PPTX shows slide content, order, notes and native objects. The
rendered slide overviews show composition, text fit, overlap, contrast, cropping
and image quality; individual slides show what the overview leaves unclear, such
as small chart labels or a suspected problem. Bounds checks cannot detect all
text overflow. Weak slides are worth revising as well as broken ones, and a
revision shows only in a new preview.

The editable deck publishes with its version-bound preview. Local LibreOffice
rendering is not a check in Microsoft PowerPoint.
