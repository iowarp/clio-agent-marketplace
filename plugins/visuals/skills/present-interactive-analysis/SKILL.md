---
name: present-interactive-analysis
title: Present Interactive Analysis
description: Use for explorable answers, generated images and SVG figures, illustrated guides, image collections, video and editable message drafts shown through the active A2UI catalog.
---

Use this skill when interaction or structure helps the person use the answer.
Data views reflect observed evidence; message drafts and guides can present
authored content for the person to edit or follow. The protocol and component
payloads are internal; the person works with the rendered view.
This guidance is about the result's presentation; it is not a required
workspace-initialization step. Independent inspections can run together, while
processing, artifact registration and display each depend on the preceding
result.

A `create_a2ui_surface` call renders inline in the chat as an interactive
view — hoverable, clickable, linkable to the session's other views.
Producing the same data through the artifact tools instead (a `.json` spec,
a rendered `.png`) makes a file in the workspace: the user sees a file
attachment, not a chart, unless a surface for it also exists. A surface fits
an ask to see, render, plot, or map something; an artifact fits a deliverable
that is itself a file the user asked to keep.
A generated visual artifact (PNG, JPEG, SVG, or another supported image)
displays through the active A2UI catalog's Image component, so the person sees
the figure in the answer and keeps its downloadable file. The Image takes the
artifact reference; a local filesystem path, a base64 copy, or an invented URL
does not load. The catalog lists its supported media formats, and an
unavailable image component is worth saying plainly.
A figure shown once in A2UI, with its downloadable file alongside it, needs no
Markdown copy in prose. A new figure on a distinct surface ID leaves its source
map, chart, or model in place; reusing an image surface replaces what it
showed, which suits revisions of that figure.

For authored SVG and HTML, CLIO's CSS variables give adaptive presentation:
`--background`, `--foreground`, `--primary`, `--muted`, `--muted-foreground`,
`--border`, `--radius`, `--font-sans`, `--font-mono` and `--chart-1` through
`--chart-5`. SVG text and neutral shapes can use `currentColor`. Explicit author
colors are preserved, so hard-coded black/white does not follow the app theme.
An SVG `viewBox` and ordinary HTML in document flow let its preview grow and
shrink with its content. Theme changes preserve live HTML controls; canvas
scripts can repaint on `clio:theme-change`. The existing artifact and surface
tools cover this; there is no separate widget tool, and the person does not
need to move code between viewers.

Component shapes are NOT in this skill — the catalog itself is the allowlist and
the source of truth (`docs/design/a2ui-compat-campaign-2026-09.md` S2/S4).
`load_skill("a2ui-catalog-<slug>")` loads a catalog's index (see "Skills available
to you" for the ids your session can currently produce), and
`load_skill("a2ui-catalog-<slug>", file="catalog.json#/components/<ExactComponentId>")`
loads one component's exact schema. The key is the complete key from the catalog
index: for example, `catalog.json#/components/clio.chart.v1`, not a display label
such as `Chart`.

`load_skill(..., files=[...])` loads several exact component schemas in one call,
instead of a separate lookup for each component or schema definition.

A revision changes a surface with `update_a2ui_components`, or
`update_a2ui_data_model` for bound-data changes; `inspect_a2ui_surface` shows
the components before and after. An update that returns a ready surface
confirms schema acceptance, not content preservation. Content the user did not
ask to change is easy to lose in an update: media references, child order,
captions, source links, units, and version or availability labels. A Text
label replaced with a Button or another component loses its qualifications
unless its visible child text or a connected Text component carries them.

A public data source the user names is usually reachable with an available
fetch tool or a local shell HTTP request; the returned status and data shape
show whether it worked, and a shell request may need the person's normal tool
approval. A view that queries more than a small inline sample reads the source
data from a registered artifact.

## Choosing a view

Views that fit the common shapes of evidence:

- A spatial result shown as point markers (stations, sites, cities) → a map
  component.
  `category`/`categoryField` hold groups and `value`/`valueField` a
  measured magnitude. Putting a numeric measure into `category` makes a
  separate legend entry for every distinct number; the numeric value gives
  the renderer a continuous colour scale. A short `valueLabel` and
  `valueUnit` label that scale; the renderer supplies the legend.
- A GeoJSON FeatureCollection of sites, paths, or regions → a map with
  `geojsonUri` pointing to the registered artifact. Feature-property fields
  can be named for labels or colour; the map draws the actual shapes.
  A custom projected chart remains available when its encodings or layers
  are the point of the analysis.
- Time-ordered positions such as hurricane or vessel tracks → a map with
  `dataUri`, latitude/longitude/label fields, `trackField` for the path ID,
  and `orderField` for an ISO-8601 time or numeric sequence. The renderer joins each path and
  keeps its observations selectable.
  An archive with many tracks reads better as a meaningful period or named
  subset that people can compare, with the full archive kept as an artifact;
  simply taking the first rows can leave paths incomplete, and an answer
  about the archive may not match the rendered slice.
  Repeated or swapped columns can look plausible in a CSV while placing the
  paths in the wrong location; a few parsed coordinates compared with the
  source show it.
- A registered 3D model or simulation mesh → an orbitable mesh viewport.
  It accepts common model formats; its `format` field settles ambiguous
  bytes, and `materialUri` names an OBJ's registered MTL companion.
  Scalar colouring, frames, and thresholds apply when the GLB contains
  CLIO FEA result fields. The exact catalog schema has its shape.
- A registered two-dimensional field, image grid, or geographic raster →
  `clio.raster-viewport.v1`, given `rasterUri`; `variable` selects a field of a
  NetCDF or zipped Zarr archive with multiple fields, and `band` one band of a
  multiband GeoTIFF. The viewer requests bounded samples while the person
  pans and zooms, and shows values and a colour legend; `unit` labels the
  values. The catalog entry has the exact accepted shape.
- Structured rows and columns → a data table.
- A quantity that changes over an index or time for a few series → the catalog's
  chart component (`clio.chart.v1`), typically its `trajectories` preset.
  Series from different calendar periods compare by shape on elapsed time or
  sample index from each series' own start; absolute timestamps stay available
  in the data and map or table.
- Many entities or grouped comparisons (one line per sample over time, spectra,
  distributions per group, a matrix of values) → the same `clio.chart.v1`
  component. A named preset fits when it communicates the comparison well.
  An authored spec fits when layering, direct labels, a reference line, a shared
  scale or a deliberate facet layout makes the evidence easier to understand,
  even if a preset could technically plot the rows. A guarded spec leaves the
  source data unchanged.
- For anything non-trivial in size, a registered artifact reference replaces
  inlined rows, and the server-side query filters, aggregates or downsamples it
  (for example, a bounded number of points per entity), so the data needs no
  trimming by hand.

- A single observed value → one metric component per value.
- A sequence of images, comparisons, or illustrated instructions → the catalog's
  `Carousel` container. Ordinary Image and Text components together make each
  captioned slide; Video can be a slide or a standalone player. Media in
  registered artifacts loads in every viewer. A carousel is useful for
  many kinds of content, not only setup guides.
  For CLIO documentation, the relevant guide and
  `https://clio.iowarp.ai/media/guides.json` (or `/media/guides.json` on a supplied
  documentation host) list the guide's actual
  image/video paths, section names, captions and available version labels.
  Relative paths resolve against that host; the matching files, obtained with an
  available fetch or shell tool and registered, display by artifact reference.
  The source-guide link and version qualification belong with the explanation.
  Screenshots come from the guide, and viewing a slide is not completing its
  instructions.
- A requested illustration, photograph, or generated schematic the person
  should inspect alongside data → an Image in the same surface. The Image takes
  the registered file's artifact URL, with a short description of what it
  depicts. A file that has not been created or registered cannot be shown.
  A generated schematic's labels need to stay clear of the title, legend, and
  edges at the displayed size; the rendered image shows collisions. The
  surrounding surface can carry the report title and readings; they need not
  be repeated inside the image.
- A weather or field-site conditions question with observed and forecast data →
  a compact weather view, accompanied by the decision-relevant answer in prose.
  The view carries the hour-by-hour and day-by-day detail, so the prose can hold
  the useful judgment, uncertainty, and source rather than repeating its rows.
  For a live named-location forecast, `get_weather_forecast` supplies the data;
  the renderer makes no weather request of its own.
  `observedAt` and every hourly `time` take an ISO 8601 UTC offset or `Z`;
  each daily date is `YYYY-MM-DD`.
- A request for email, chat, or text alternatives the person can revise → a
  message-draft view with labelled versions. The person edits the draft in
  place and decides whether to copy, use, or open an email version in their
  chosen mail app; CLIO does not send it.
- A protocol, recipe, or setup guide with steps the person will perform → an
  interactive steps view, especially when timers or quantities matter. In a
  recipe, measured materials in `ingredients` and actions in `steps` keep the
  completion count on cooking rather than the shopping list. Amounts that
  change with the scale go in quantity fields. Step details stay true after a
  changed count when they give the per-unit instruction: if `quantity` shows
  8 mL for 4 samples, “Add 2 mL to each tube” in `detail` stays right, while
  “8 mL total for 4 samples” does not. The fixed per-unit instruction matters
  when the starting count changes. In a recipe, a fixed cup/tablespoon/egg
  equivalent in `detail` beside a scaled amount goes stale when it scales;
  singular and plural labels for countable units read correctly at one and
  many. An adjustable amount's title reads correctly at any count when it does
  not name the count (for example “Tomato pasta” rather than “Tomato pasta for
  two”); the control displays the current servings. Grouped related prep keeps
  the checklist easy to scan.
- A parameter the person should adjust while inspecting a result → a bound
  slider; its two-value range mode gives an interval. A date or time cutoff
  can use `DateTimeInput`. The component schemas give their value shapes; the
  bound values feed the view's data query.
- Ongoing/completed work, a warning, or a diff → the matching status/callout/diff
  component.
- A durable nonvisual export (a document or data file) → a registered artifact
  reference. Generated visual exports also use the Image guidance above.

### How filters work

Useful filters follow the scientific question, not the component type: what a
reader would narrow to isolate a phenomenon, compare cohorts, or check an
outlier, judged from the available fields, their units and values, and the
range or number of distinct values in the displayed slice. A few interpretable
dimensions are usually enough. A row ID or nearly unique label is rarely
a useful filter; a coordinate, measurement, or time field may be useful when
the question calls for a spatial, numeric, or temporal range. Time precision
matches the data and question: years for a multi-year archive and dates for a
shorter span. A sub-day cutoff is an exact interval in `dataQuery.filter`,
shown with the observation timestamps.

Filter fields need to be in the registered artifact and the view's projected
`dataQuery.columns`. On a referenced map, `filterFields` names the real columns
worth narrowing; the viewer creates the controls and applies them to the map
and `Reference this`. If omitted, it exposes its default map fields. A map with
filters on measured columns needs `dataUri`, even for a small dataset: inline
points do not carry arbitrary measurements. A referenced map,
chart, or table needs a registered CSV or Parquet table; a source JSON file is
not a queryable table. A suitable workspace table, with provenance and columns
that answer the question, can save a new external search. Numeric columns
written as numbers and timestamps as ISO-8601 strings with an offset stay
queryable; a conversion can silently turn a timestamp into locale-formatted
text, which the registered table's schema and a sample row show. A chart exposes
native filters for encoded fields; a table exposes them for displayed columns,
so a field is visible there only when it is in an encoding or table column
list. Filter controls come from the viewer; the component spec has no filter
buttons or actions. `dataQuery.filter` sets the initial scientific slice, and
the viewer handles later exploration. The visible rows, counts, and
`Reference this` payload describe the same filtered subset when the filter is
set up right.

### Answering a question from a selection

**Reference this** is a pointer to evidence. Its preview and projected
columns describe the current view; they are not the complete source dataset.
The referenced artifact's schema and the selected records hold the full
detail. The reference's filters and stable row IDs select the same rows in a
query, and a wider column projection reaches fields that the view did not
display. For example, a rate needs observation times as well as measured
values. A field absent from the preview may still be in the source; only the
source shows whether it is, and what it lacks limits what the evidence
supports.

A new view helps when it makes the explanation easier to inspect; repeating
the original dashboard or the reference's technical payload adds nothing.

## Composing surfaces

A report rests on the reader's question, the supported finding, and what each
view contributes. `create-dashboard` covers a substantial saved report, and its
`references/report-design.md` has composition examples. Colour, size and
emphasis read best with consistent jobs across related views. A collection
of correctly plotted charts is not yet an explained report.

A small surface at the step it explains keeps evidence beside its
explanation; a stable semantic `surface_id` updates that view in place.
Unrelated work accumulated into one final tabbed dashboard loses that. Tabs
suit several views of the same result that belong together, when the available
width justifies them.
For a briefing or report that asks for several related views, Row, Grid, or
Tabs compose the relevant metrics, media, map, chart, and table where that makes
comparison easier. Each view carries its own detail, so a generic heading
around it repeats. The user's named measurement is the one for titles, legends,
and captions; when only units are given, it is a reading, not an unstated
physical phenomenon.
Several components on one surface need a layout `root` component that
references every child by id. A second unconnected component is not visible;
the producer names unattached ids so the tree can be repaired.
`inspect_a2ui_surface` finds an existing surface's id and current components;
updating that surface replaces the earlier view, so a correction in a later
turn does not leave two versions competing in the chat.

## Custom charts with Altair

The general chart component renders **Vega-Lite**. When an authored view explains
the result better (a layered overlay, direct labels, a facet layout), **Altair**
writes the chart in Python and exports the Vega-Lite spec the component takes,
which is easier than writing Vega-Lite JSON by hand.

- **Data comes only from the component.** Every chart builds on
  `alt.NamedData("source")`. A DataFrame, URL or inline values passed to
  `alt.Chart(...)` get inlined into the spec, and the server's chart guard
  refuses them. Rows arrive through the component's inline data or its
  artifact reference.
- **Layout keys the guard allows.** Past the usual mark/encoding grammar,
  the guard also allows `facet` + `columns` (a wrapped small-multiples
  grid), `spacing`/`padding`/`align`/`bounds`/`center` (composition
  layout), and `projection` (a geoshape or lon/lat point map) at the top
  level. No `url` anywhere, in any of them.
- **A choropleth from inline rows.** A row's cell can hold a GeoJSON
  Geometry object instead of a scalar, so a `geoshape` mark can draw real
  shapes straight from rows the agent already has, no artifact needed.
  `projection` sets the map projection; the renderer fits the map to the
  geometry actually present in the rows, so `projection.fit` stays unset.
- **Shared selection.** Charts, maps and tables reading the same artifact
  automatically link through its stable `__row` key. A custom chart gains a
  point selection from the renderer when it has a selectable field; the
  renderer also supplies box selection, zoom and Reference this.
- **Spec size.** The guard caps size, nesting and view count.

`vega_spec.py build` exports and pre-checks a Python file that assigns the
Altair chart to `chart` (`SKILL_ROOT` is this skill's directory):

```text
uv run --no-project --with "altair>=5" --with "clio-schemas>=0.5.2" python "SKILL_ROOT/scripts/vega_spec.py" build "CHART.py" "SPEC.json"
```

The pre-check calls the same guard the server runs
(`clio_schemas.a2ui.chart_spec.check_chart_spec`), so it names the same rule
a server refusal would instead of a hand-copied approximation;
`vega_spec.py check SPEC.json` re-checks an existing spec. The server's
guard is still the final authority. The chart component's schema, which the
spec goes into, is in the catalog skill.

## Linking views on one surface

Views on one surface that show the same observations link when built from
one shared dataset. The renderer links chart, map and table selection by the
artifact's stable `__row` key when they use the same `dataUri`. Small inline
views also link when each has the same set of unique entity values, even if
the rows appear in a different order. This is normal interaction; the person
does not need to ask for linking, and no selection controls or selection path
need adding. The user can click or box-select a chart, map or table,
see matching rows highlighted, and use Reference this to carry those rows and
active filters into the next message. For larger or evolving data, one shared
artifact keeps stable identity through filtering, sorting and pagination.
An explicit `/selection/` path with matching `selectionField` values links
separate datasets that share a concept across different columns or files.
Views on different surfaces keep separate selection state.

## Preserving a user's choice into the next turn

A click or selection inside a surface is local visual state only — it does not by
itself reach the agent. A choice reaches the agent through a submit action whose
event delivers the resolved selection as structured context; the catalog's
Button/action and selector schemas, loaded together, show how the two wire up.
The selector's value has to be bound to the same data-model path read by the submit action; a path mentioned only by the action has no selected value to deliver. An ID alone can lose the detail the
person just saw, so the selected item's displayed fields in that context help a
follow-up that asks about them. `inspect_a2ui_surface` reads the existing view
for details beyond a selected ID; a field visible in that view is available even
when the submit event carried only its ID.

## Producing and verifying

`create_a2ui_surface` takes one coherent revision per call (an empty
`catalog_id` uses the session's negotiated catalog). `rendered=true` and
`state=ready` mean the definition was accepted. These values do not
establish that anyone inspected the browser's rendered pixels.
The `review-visual-presentation` skill covers complex views, visual
investigation and dashboards: `inspect_a2ui_surface` reads the current viewers
and bindings, `capture_a2ui_surface` the matching pixels, and supported
controls or component definitions change with expected revisions. That holds
for maps, charts, tables and images as well as 3D views. The underlying data,
not the picture, settles the question's answer.
When dense graphs obscure the result, a meaningful slice with useful detail
behind supported filters, selectors or tabs reads better.
Supported annotations point to evidence in explanations and questions without
changing the original data or who owns the question's answer.
A refusal names what to load
next (`hint`); that component's schema shows what to correct. A refused payload
printed as chat text renders nothing, a static image silently swapped in for an
interactive component loses the interaction, and a refusal is not a success.
