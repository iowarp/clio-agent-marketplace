# Build and review the report reference

The example contains fictional station summaries in arbitrary units. It
demonstrates connected report prose, a chart derived from those summaries, native
headings and tables, captions and page numbering. It is not a real experiment.

It runs from the returned JavaScript workspace, where `docx` and `sharp` resolve,
once the prepared runtime reports JavaScript ready; this skill's file argument
loads `create-reference-report.mjs`. Executed with the returned
`javascript.script_argv` and an output directory, it writes
`reference-report.docx`, `reference-chart.png` and `reference-source.json` there.
`prepare_document` with `action="render"` on the DOCX produces its contact sheet;
individual pages show what the overview leaves unclear. Fonts and renderer
changes can change pagination; the checked reference renders as two pages.
Layout fixes belong in the native builder and show after regeneration. The final
editable DOCX publishes with its source-bound PDF preview.

`references/docx-js.md` covers library mechanics and `references/report-design.md`
content and composition. The example's fictional findings left under a new title
are not a user report.
