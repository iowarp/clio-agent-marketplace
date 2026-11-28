---
name: create-dashboard
title: Create Dashboard
description: Author and revise a substantial interactive dashboard in the side panel using existing A2UI components, composed layouts, shared data bindings and linked views.
---

Use this skill when the person wants a dashboard or consolidated interactive
report. Author an interconnected presentation of substantial data, with a clear
overview and useful detail. The dashboard is an artifact alongside chat, with
the existing A2UI semantics throughout. Develop it over as many tool calls as
useful; a dashboard is not limited to one or two graphs or one generation call.

Inspect relevant earlier views with `inspect_a2ui_surface` and read their
referenced data. Decide what tells the story: retain meaningful comparisons,
remove repetition, add explanations, and generate new evidence-based figures
when useful. For example, show an original shape once with two chosen evolutions.
Units, source identity and limitations carry the evidence's meaning. A made-up
measurement, or a derived visual presented as part of the original recording,
misstates the evidence.

The reader's question and the supported finding shape the rest: the role of
each panel, shared colour meanings, useful annotations and the initial level of
detail. `references/report-design.md` has worked layouts using this catalog. A
few complementary views say more than repeated views of the same data. A custom
guarded chart can explain a finding better than a preset; a technically fitting
preset is not a design requirement. `references/bike-station-report.json` and
`references/bike-stations.csv` are a complete small example. They connect one
clearly synthetic dataset to an annotated time chart, station balance, map and
exact source table; their measurements are fictional, not findings. Shared
automatic colours keep their meaning when related maps and nominal chart
encodings use the same category labels.

Load the active catalog index and exact component schemas with `load_skill`.
The catalog remains the authority for shapes and actions. Reuse its rows,
columns, frames, grids, text, metrics, charts, tables, meshes, images and inputs.
A connector's live view (an MCP App, such as a 3D scene) is a component too:
`clio.mcp-app.v1` mounts the view itself, and its state channels link it to the
other views on a shared path such as the selected time; an exported image of it
is a still picture that links to nothing.
One composed report keeps related evidence visible together, so a person can
compare it without switching tabs and a PNG tells the same story. Tabs suit
genuinely separate workflows or optional depth; a tab that separates a chart
from the map, image or comparison needed to interpret it hides that context.
The main finding and its supporting views read best in the initial space.
Component payloads are authored here; the person works with the rendered view.

The `review-visual-presentation` skill covers rendered review. A bound
`Tabs.activeTab` lets a review select tabs. `inspect_a2ui_surface` and
`capture_a2ui_surface` read the overview and each tab; a published version is
captured by its exact `artifact_id`, and revisions are immutable. The docked
view and an expanded one can differ. Surface acceptance alone does not
establish readable pixels. A clear report also explains: the finding is
apparent, every panel earns its space, and labels, colour meanings, units and
filters agree. A useful default view reads better than every graph or series
at once; the source data stays available, and supported tabs, filters,
selectors or optional-view controls reveal more detail. Visibility properties
come from the catalog, and an answer found only in hidden content is easy to
miss.
Annotations and linked selections can connect an explanation or question to
specific evidence; they do not replace the question's explicit answer action.

Choose the layout that fits the content. A single full-width diagram, equal
columns, a simple vertical report and uneven columns are all valid. Give wide
workflows and dense diagrams enough width to keep their labels readable. Use
unequal `Row` child `weight` values when one view needs more space, and `Grid`
for equal comparisons. These are options, not a template to reproduce. Weights
are relative shares, not grid spans. Put related evidence and its controls
together. The actual docked and expanded layouts show whether stacking panels,
changing proportions or separate views would help. Dividers, lists, images,
icons, and modals remain available when they serve the presentation.

Write an editable JSON document inside the workspace:

```json
{
  "format": "clio.dashboard.document.v1",
  "title": "Design evolution",
  "catalog_id": "ACTIVE_CATALOG_ID",
  "source_surface_ids": ["earlier-comparison"],
  "components": [
    {"id": "root", "component": "Column", "children": ["summary", "analysis"]},
    {"id": "summary", "component": "Text", "text": "An evidence-based summary."},
    {"id": "analysis", "component": "Text", "text": "Replace this with your composed linked data views."}
  ],
  "data_model": {}
}
```

A document has exactly one `root` component. The whole dashboard shares one
ordinary A2UI data model, so related controls and views can bind to the same
paths through the catalog's existing selection and query/filter contracts.
Linked datasets need a real shared entity field; matching row numbers in
unrelated datasets does not establish a relationship. Mesh views with a shared
`syncGroup` rotate and zoom together, including views authored from results
produced hours apart.

A report can reference full registered source data; nothing needs sampling to
fit it. Small inline tables remain allowed by the catalog. Additional images or
charts come from real analysis and normal artifact registration, and a
derivation is distinct from observed evidence. The dashboard's views already
show in the side panel; repeated inline in chat they appear twice.

A dashboard can follow data that keeps changing. A chart or table whose `dataUri` is
`study://<study>/measurements`, `/entries` or `/records/<name>` reads a science-log
study as it is now and shows new entries as they arrive, so a dashboard that is a
study's view (attached with `log_entry`, `type: view`, `dashboard_id`) needs no
republishing to stay current. A source with no rows yet is accepted and reported in
the result as `study_sources_unchecked`: its columns are checked once rows exist.

A source can also be a file or a stream. `artifact://artifact_<id>` shows one fixed
version. `artifact://<workspace>/<name>@latest` follows the newest version of that
file, and a `dataUri` path written as `data/status.csv@latest` binds it that way.
Writing the file does not make a version: `create_artifact(path=...)` registers one
per rewrite (a script that rewrites it often gets one version per interval). A
stream's `view_uri` (from `open_stream`) is such a reference: its chart or table
updates from the stream's newest record entries while the dashboard is open. A stream
is read as it is stored, with no `dataQuery`; the chart spec reshapes its records
(for example a fold or a time axis). The result's `data_bindings` says which views
are `live` and which are `pinned`.

`publish_dashboard_report(definition_path="reports/design.dashboard.document.json")`
validates and publishes an immutable artifact version; its artifact reference
opens the dashboard in the side panel. It returns a report id and the source
path. Publishing an edited source again with that `report_id` adds a version
to the same report, and earlier artifact versions remain available; an owned
dashboard artifact reference also resolves the report family. Saved inspection
returns these identities under `artifact`. A newly published report opens in
the currently viewed conversation. A capture reads the fresh viewer that an
inspection finds; a disconnected client or different conversation cannot
supply pixels.

A published artifact's own viewer, tabs included, is inspected with
`artifact_id`. `update_a2ui_data_model` with that artifact id, the inspected
surface revision, viewer id and `expected_view_revision` navigates its
declared local bindings, and a capture then shows the changed view. Each
update targets one exact path listed in the inspection's `controls`; replacing
their parent object is not a supported control update. Each change makes a new
viewer epoch, which a fresh inspection returns for the next control change.
Local navigation preserves the saved artifact version; changing its authored
contents means editing the source and publishing a new version.

The viewer supplies standard Reference this and labelled image capture actions
for the dashboard and its individual views. References identify the artifact
and source document as well as the selected component or data zone. These let
the person ask you to revise part of the system or produce a new derived visual.
PNG downloads capture the displayed dashboard; self-contained HTML includes the
entire dashboard, its tabs and interactions, and referenced data. Missing
dependencies are reported rather than silently omitted from an export.

Corrected versions stay in the same report family; earlier versions remain in
Versions and Observability. Review captures are retained verification evidence.

The published report already retains its source path, so the editable source
needs no artifact of its own; registered as a deliverable it shows as a second
card. `create_artifact(..., purpose=...)` marks review files as
`"verification"` and working files as `"intermediate"`; a requested
image/PDF/HTML export is a deliverable and uses `purpose="deliverable"`.
