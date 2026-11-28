# Build and review the presentation reference

The example contains six slides using fictional station summaries in arbitrary
units. Its native tables and chart stay editable; speaker notes retain the source
context and uncertainty. It is a design example, not a real experiment.

`create-reference-deck.mjs` loads through this skill's file argument. Once the
execution runtime reports JavaScript ready, it runs from the returned JavaScript
workspace, where `pptxgenjs` resolves. Executed with the returned
`javascript.script_argv` and a task-owned output directory, it writes
`reference-deck.pptx` and `reference-source.json` there.

Reopening the deck shows its six slides, tables, chart and notes. `prepare_document`
with `action="render"` gives its six-slide contact sheet; individual slides show
what the overview leaves unclear, such as small text or possible layout problems.
Changes go into the native builder and appear after it runs again. The final
editable deck publishes with its source-bound PDF preview.

`references/pptxgenjs.md` covers library mechanics and `references/slide-design.md`
narrative and composition. A real deck's slide count and layouts follow from its
evidence and audience; the example's findings are fictional.
