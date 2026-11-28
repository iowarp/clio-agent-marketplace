---
name: work-with-spreadsheets
title: Analyze and create spreadsheets
description: Create, edit and analyze Excel workbooks and CSV/TSV tables, preserving formulas and checking calculated values and rendered sheets.
---

# Work with spreadsheets

`prepare_document_runtime` returns the prepared Python environment, which
contains `openpyxl`, and runs scripts with `python_argv` (uv selects the prepared
Python). Its reported host paths describe this session; a repository's `uv run`
may select another environment. Its returned output directory is for intermediate
files; `.tmp` is scratch space, and requested deliverables live in the active
workspace outside it.

`prepare_document(path, action="inspect")` inspects a workbook; for large
files `sheet` and `cell_range`, such as `sheet="Budget"` and
`cell_range="A1:H50"`, bound it. The returned content JSON reads in bounded
sections. It reports formulas separately from cached values and detects external
links. The helper refuses excessive cell ranges rather than silently truncating
them. CSV/TSV inspection preserves row boundaries; these formats carry no workbook
styles, multiple sheets or formula caches.

Loading with `data_only=False` keeps formulas, and `keep_vba=True` keeps an
`.xlsm`'s macros. A workbook loaded with `data_only=True` and saved loses its
formulas. Input cells, formulas, merged ranges, tables, named ranges and existing
formatting are all part of the workbook. A merged cell is written through its
top-left anchor. Re-saving with a library can alter features it does not support,
such as macros, external links and unsupported objects; the original file keeps
them.

A new workbook reads well with clearly named sheets and units, appropriate number
formats, and editable inputs separated from formulas. Formulas let outputs update
with inputs. Representative results checked against independently calculated
expected values show whether the formulas do what was intended. Formatting a cell
as a percentage does not change its value: fifteen percent is stored as `0.15`.
Cross-sheet names containing spaces are quoted.

`openpyxl` writes formulas but does not evaluate them.
`prepare_document(output_path, action="recalculate")` creates a new XLSX copy
using an isolated LibreOffice profile, preserves the input file and checks every
formula cache plus error cells. It reports `status`, `formula_count`,
`issue_count`, and a bounded issue list. A failed manifest is not a checked
workbook. The returned recalculated path holds the checked bytes, which are the
ones to place at the final workspace destination outside `.tmp`; resaving that
copy with `openpyxl` clears the calculated caches.

Recalculation evaluates the workbook but does not prove its formulas are correct.
An error-free result can still reference the wrong cells; representative totals
and edge cases compared with the task's intended calculation show that.
External-linked files are refused by automatic recalculation because conversion
can lose their cached values and relationships. Macro-enabled files are also
refused by this helper; a silent conversion would drop what makes them
macro-enabled.

Clio uses bundled LibreOffice or provisions a private verified copy for rendering
and recalculation; either can fail, and the result says so. Print areas and page
settings shape `prepare_document(path, action="render")`, whose sheet pages show
through `view_image` or `view_pdf`. Rendering reflects print layout, not the
entire interactive workbook. Without the converter or a visual tool, only what
was actually checked is known; the editable workbook remains the deliverable.

`create_artifact(path=output_path, kind="report", pdf_preview=true)` designates
the final XLSX. It registers the editable workbook and its version-bound PDF
print preview for Clio's viewer; `pdf_previews` reports failures. Clio shows a
published artifact's card when the final response names it. The runtime's
workspace-file or registered artifact/resource citation format makes references
clickable; browser-local `file://` links are not. A CSV/TSV registers directly as
the table. Supplied data has provenance; assumptions introduced while working are
not the user's data.
A separately registered review PDF does not bind to the editable workbook;
`pdf_preview=true` on the source call, or on its batch item, creates that
relationship.
The requested editable workbook is the deliverable. PDFs made only for review or
display are derivatives of it; registering one separately lists it as another
deliverable. `used` names the actual source documents or data; the review PDF is
derived from this output, not a source of it.
