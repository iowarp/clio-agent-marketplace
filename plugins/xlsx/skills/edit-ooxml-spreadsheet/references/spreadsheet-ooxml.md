# SpreadsheetML invariants

- Worksheet identities are linked through `xl/workbook.xml` and workbook relationships; sheet labels alone are not stable identity.
- Strings may be inline or indexed through `xl/sharedStrings.xml`.
- Cell appearance references workbook styles by index. Rebuilding styles can shift unrelated cells.
- Formulas and cached values are distinct. Recalculation refreshes cached values; the calculated output is checked separately from the formulas.
- Dynamic arrays, data models, slicers, Power Query, external links, threaded comments, rich data types, and advanced charts may exceed `openpyxl` round-trip support.
- Macro-enabled workbooks must retain VBA parts and content types; a `.xlsx` must not be mislabeled as `.xlsm`.
- Changing a table range may require updates to table definitions, names, formulas, drawings, and charts; any dependent reference left behind points at the old range.
