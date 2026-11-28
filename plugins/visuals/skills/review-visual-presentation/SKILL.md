---
name: review-visual-presentation
title: Review figures and layouts
description: Use during visual investigation or for substantial dashboards, to inspect, capture and refine complex data views at the user's viewing size before presenting them.
---

Visual interaction helps both to investigate a question and to improve what a
person will see: the evidence and the current view, a change to a declared
control or component, and the resulting image each inform the next change.
Changes that resolve a concrete uncertainty or presentation problem are the
useful ones. This applies to maps, charts, tables, images, models and
interconnected reports.

## What a capture shows

For a substantial authored dashboard or diagram, the published viewer's
capture at the width the person will use is the closest view of what they
will see:

- The returned image shows the result; its URI, source JSON or tool success
  does not. In it you can see whether the main idea is apparent, text is
  readable, the whole diagram fits, and empty space or narrow columns obscure
  relationships, and whether a full-width view, equal panels or a simpler
  arrangement would explain it better.
- The surrounding frame and component headings belong to the view as much as
  the plotted marks: a title cut off with an ellipsis is a defect even when the
  graph fits. A label that is visible may still be too small to read.
- A column-count change helps only when it fixes an observed problem.
- Docked and expanded arrangements can differ; readability in an expanded image
  does not establish readability in a narrow pane.
- Declared controls and linked selections can be exercised in the viewer. A
  workflow folder link's target is checkable with filesystem tools, and with
  interaction tools, clicking it selects that folder in Files. A highlighted
  box alone does not show that navigation happened.

Schema validation, a capture receipt and an uninspected image do not establish
visual quality. A small inline diagram does not call for a dashboard or an
elaborate layout recipe.

## Acting on a figure comment

A comment on a figure arrives as a "Review of ..." block: an overview with each
mark labelled, a crop of each mark at twice its size, and a "Produced by" line
naming the call and script that made the image. The crops show what the person
means. The producing script or `run_code` cell is the source of the figure;
running it again writes the figure to the same path, where `view_image` shows
the new output. Each comment carries a label (S1, S2, ...). When the producer is
unknown, the script that makes the figure is the thing to ask about; edited
pixels do not change the source.

## Surface state and capture

`inspect_a2ui_surface` reads the current surface; the active catalog schemas
describe its components. `update_a2ui_components` replaces complete
definitions for the named components, so properties, references and links
left out of the new definition are dropped. `update_a2ui_data_model` changes a
declared binding. Shared filter and selection semantics already exist. A saved
dashboard is immutable: a definition change goes into its source document and
is published as a new version.

A producer's `rendered=true` means the definition was accepted, not that
anyone inspected its pixels. `inspect_a2ui_surface` reports fresh mounted
viewers, declared bindings, current values, cameras, active tabs, data
references and readiness, for each viewer when several are open.
`capture_targets` supplies the exact capture arguments for each visible
matching viewer; a guessed view epoch does not match. Updates take the
inspected revision, and `capture_a2ui_surface` captures the new revision. Its
result attaches real pixels to the next model step and retains a hashed image
artifact with the viewer state. For a saved dashboard, inspection and capture
take its immutable `artifact_id`. A temporary live surface is where a saved
definition's changes can be reviewed before the document is published as a
new version.
In an open saved dashboard, `update_a2ui_data_model` with its `artifact_id`,
surface/revision, selected `viewer_id` and inspected `expected_view_revision`
navigates or changes declared controls. This changes only that view's local
binding; its acknowledgement gives the new epoch to capture. It does not edit
the immutable artifact or submit a question answer.
`Tabs.activeTab` binds the visible tab; its value is a tab child id.
`clio.map.v1.camera` binds a map's pan, zoom and rotation, and a shared path
moves several views together. Reference-backed queries and selections stay
authoritative. An image URI, export link or unrelated earlier screenshot is
not visual inspection; the capture's revision and state show which view it is.
Map and mesh cameras can have different binding paths and shapes in the same
dashboard, so the inspected component's exact path is the one that moves it;
replacing the root data model with a guessed set of properties loses the rest.
The captured camera, frame and filters show whether a requested change took
effect. A declared control that did not move usually points to the binding or
the update.
For multiple tabs or camera positions, each returned capture's control values,
view revision and image hash identify which view it shows. Repeated tool
arguments or an earlier screenshot are not evidence of a new view.
For a viewer that is still loading, `expected_view_revision=null` (or omitting
it) lets capture wait for readiness within its deadline. A pinned view epoch
matches an already-ready human view exactly; a loading epoch becomes stale as
tiles or layout finish.
After publication, the newly opened viewer can still be mounting. A single
`a2ui_view_stale` or `a2ui_render_not_ready` result usually clears once the
same immutable artifact is inspected again and capture uses its current viewer;
with `ready` false, `expected_view_revision=null` waits rather than pinning
zero. A viewer that is absent or still cannot supply pixels is a real
limitation. After a declared tab or camera change, the acknowledged epoch, or a
fresh inspection, identifies the view to capture.
Without capture or a requested control, supported structural corrections are
still possible and the verification gap remains. A map the person can zoom is
not a camera the agent controls.

## What a useful view shows

The size the person will use is the size that matters: the overview, relevant
tabs, labels, legends, units, contrast, clipping, framing and controls. A
useful view answers the question and lets the reader find the important
comparison without deciphering a dense wall of marks.
The explanation is part of the view: what conclusion a person can see in the
image, which marks support it, and what uncertainty remains. Related panels
are comparable when their category meanings, ranges, dates and selected records
agree. Direct labels or reference marks reduce the effort of finding the
evidence; redundant panels take space from the central comparison. The
dashboard skill's `references/report-design.md` covers report composition.
Composition works as a whole when related charts, images, viewports and text
can be interpreted together without tab switching, which a whole-report image
shows better than individual views. Unequal row proportions help when expanded
and readable stacking when docked. Essential evidence behind an optional tab
is missing from the initial view and PNG.
A person usually expects a complex visual to have been checked already, without
asking for a screenshot review.
A crowded view reads better as a meaningful subset or aggregate first, with the
complete source data retained and the initial slice explained. Additional
series, layers or views fit behind catalog-supported selectors, filters, tabs
or optional-view controls, with readable labels and visible inclusion state.
The catalog has no generic visibility property, and hidden contrary evidence
misleads. The revealed detail needs to read as well as the quiet default.

Annotations point to evidence during explanations and questions. A chart can
take supported layered marks for a labelled point, red outline, range or trend
while its original rows and quantitative encodings stay intact. A mark in real
data coordinates or stable entity IDs follows zoom/filter changes; a
pixel-positioned mark belongs to one captured viewport and identifies nothing
on a different view. Annotations clarify evidence; they do not change
measurements or submit an answer. `ask_user` owns question submission
independently.

`references/investigation-patterns.md` in this skill has worked decision
patterns. Once the question is resolved and the relevant views are readable,
further captures add nothing unless they answer a remaining concern. Visual
observations, calculations and unresolved uncertainty are different kinds of
evidence.

## Where captures and review images live

`capture_a2ui_surface` retains its screenshots as verification evidence, so
they are not separate outputs. Other review images/PDFs fit
`create_artifact(..., purpose="verification")`; working files fit
`purpose="intermediate"`. Both remain accessible in Observability and lineage.
Requested images/PDFs use `purpose="deliverable"`. A revised output in the same
artifact family/name presents its latest deliverable version while Versions and
Observability retain earlier attempts.
