# OpenDocument package rules

- `mimetype` should be the first ZIP member and stored without compression.
- `META-INF/manifest.xml` declares package files and media types.
- `content.xml`, `styles.xml`, `meta.xml`, and `settings.xml` have distinct ownership; do not rewrite all four for a local text edit.
- Text annotations use `office:annotation`; change tracking uses dedicated tracked-change structures.
- Spreadsheet formulas use OpenFormula semantics and cached values; verify recalculation in LibreOffice.
- Presentation page/draw objects may inherit styles and master pages.
- Preserve `META-INF/documentsignatures.xml`, macros, RDF, and embedded objects or explicitly block the edit if the toolchain cannot round-trip them.
