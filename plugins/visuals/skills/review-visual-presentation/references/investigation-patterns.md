# Investigation and presentation patterns

## Map: which storm passed near Chicago?

The archive's time, position and storm-identity columns, and what the question
means by "near", decide what can answer it. A useful period with complete
tracks from the registered data gives the comparison. The declared query
bindings narrow region and time; the map can be centered or zoomed only if its
schema exposes that control. A candidate's real records, selected from the
view, carry its distance and time, and the numbers settle which storm it was.
A cropped track or nearest-looking line alone cannot establish the answer. An
annotated location or track makes the explanation easy to inspect.

## Chart: is this relationship correlated or linear?

Units, paired observations, missingness and grouping shape which encodings
work. A scatter plot is the usual starting view, with a readable subset or
aggregation when overplotting obscures it. Each change of filter, group or
scale produces a different view, and its counts and slice identify what it
shows. The correlation and fitted relationship come from the data; a trend and
residual view show whether the linear form holds. An apparent pattern, a
numerical result and a causal claim are three different things. A marked
outlier or range shows what the evidence changes.

## Pointing at a chart

The existing chart component can use a guarded Vega-Lite layered spec.
`examples/annotated-scatter.json` shows an unfilled red circle and label
around an existing observation using its stable ID, with all base rows kept.
Its names and rows are synthetic examples; the fields and labels come from the
actual data, the named `source` data input stays, and the catalog's chart
guard checks the result. The mark's size is a screen area; its center follows
data scales. This is not a generic canvas-overlay API.

## Dashboard: make a dense report useful

The overview at docked width, each relevant tab and the expanded view can each
show different problems: repeated graphs, unreadable legends, clipped labels
and views that do not help a reader make the intended comparison. Less
redundant content, concise interpretation, and useful detail behind supported
navigation or optional-view controls make it readable. The agent chooses the
presentation; the person can reveal the detail. Linked selections and shared
controls keep a change meaningful across views. A saved report keeps its
source lineage, and a corrected definition is published as a new version.
