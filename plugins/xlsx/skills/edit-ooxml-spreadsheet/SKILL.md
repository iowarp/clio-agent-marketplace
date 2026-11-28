---
name: edit-ooxml-spreadsheet
description: Use to create or revise .xlsx workbooks, or review selected cells and ranges, preserving formulas, styles, comments, charts and macros for Microsoft Excel.
---

# Edit OOXML Spreadsheets

- `$inspect-office-package` inventories an existing workbook's sheets, tables, named ranges, formulas, charts, external links, macros, comments, and calculation settings, and compares the package after an edit.
- A comment entry names cells (`Source: sheet Data, cells B2:D9`, or `In file: cell B2` for a native comment); exact worksheet identity and cell range resolve them. A renamed or similarly labeled sheet is not the anchored sheet; whether the comment applies there is the person's to confirm.
- `openpyxl` with formulas intact (`data_only=False`) handles supported workbooks; `keep_vba=True` keeps macro-enabled input. When package comparison shows unrelated drift, targeted worksheet XML mutation avoids it.
- Formulas replaced with cached values stop updating. Number formats, validation, conditional formatting, protection, tables, merged ranges, names, and external-link semantics are part of the workbook.
- Headless LibreOffice, when available, recalculates. A library save does not prove cached results, chart ranges, or calculation chains are correct; caches stay stale until Excel or LibreOffice recalculates.
- A package comparison with a narrow allowlist shows drift; representative formulas, totals, blank/error values, hidden sheets, print areas, and chart references show whether the content is right.
- The real workbook is canonical.

[spreadsheet-ooxml.md](references/spreadsheet-ooxml.md) covers formula and package invariants.
