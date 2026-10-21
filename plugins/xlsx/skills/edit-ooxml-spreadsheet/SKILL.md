---
name: edit-ooxml-spreadsheet
description: Create or revise Office-compatible XLSX workbooks while preserving formulas, styles, comments, charts, macros, and calculation semantics. Use for .xlsx creation, selected cell/range review, formula changes, or workbook deliverables that must open in Microsoft Excel.
---

# Edit OOXML Spreadsheets

1. Preflight existing workbooks with `$inspect-office-package`. Record sheets, tables, named ranges, formulas, charts, external links, macros, comments, and calculation settings.
2. Resolve `sheet-range` anchors by exact worksheet identity and cell range. Never redirect an anchor to a renamed or similarly labeled sheet without user confirmation.
3. Use `openpyxl` with formulas intact (`data_only=False`) for supported workbooks; use `keep_vba=True` for macro-enabled input. If package comparison shows unrelated drift, use targeted worksheet XML mutation or stop.
4. Never replace formulas with cached values. Preserve number formats, validation, conditional formatting, protection, tables, merged ranges, names, and external-link semantics unless explicitly changed.
5. Recalculate through headless LibreOffice when available. A library save does not prove cached results, chart ranges, or calculation chains are correct.
6. Compare the package with a narrow allowlist and validate representative formulas, totals, blank/error values, hidden sheets, print areas, and chart references.
7. Save the real workbook as canonical and report whether recalculation was performed or remains required in Excel/LibreOffice.

Read [spreadsheet-ooxml.md](references/spreadsheet-ooxml.md) for formula and package invariants.
