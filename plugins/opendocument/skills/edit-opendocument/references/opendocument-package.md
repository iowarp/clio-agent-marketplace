# OpenDocument package facts

- `mimetype` should be the first ZIP member and stored without compression.
- `META-INF/manifest.xml` declares package files and media types.
- `content.xml`, `styles.xml`, `meta.xml`, and `settings.xml` have distinct ownership; a local text edit touches `content.xml` only.
- Text annotations use `office:annotation`; change tracking uses dedicated tracked-change structures.
- Spreadsheet formulas use OpenFormula semantics and cached values; LibreOffice recalculation refreshes the caches.
- Presentation page/draw objects may inherit styles and master pages.
- `META-INF/documentsignatures.xml`, macros, RDF, and embedded objects survive only a toolchain that round-trips them; otherwise the edit is blocked by that incompatibility.
