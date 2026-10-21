---
id: earthscope-skills.views
section: domain
when: {"tools": ["create_a2ui_surface"]}
---
Offer an interactive table, map, metrics, plot, workflow or artifact view when
it genuinely helps; the user need not ask for it or know the protocol. For
station selection, load the catalog skill `a2ui-catalog-earthscope-stations`,
which carries the `StationMap`/`StationPicker` recipe and the
`earthscope.stations.selected` event; for other views load
`present-interactive-analysis`. Never guess component props or ask the user to
dictate payloads. Place a view right after the evidence it explains: a small
map after spatial resolution, a station view after ranking, a data-backed chart
after profiling a series. A static plot is an export, not the default view of a
series. Reuse each skill's stage-specific surface id to update in place; do not
pile unrelated results into one tabbed surface. A view complements the answer
and never holds fabricated rows; use `create_artifact` for requested reports.
