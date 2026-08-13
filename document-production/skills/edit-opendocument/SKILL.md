---
name: edit-opendocument
description: Create or revise ODT, ODS, and ODP files as native OpenDocument artifacts while preserving package metadata, styles, formulas, comments, and media. Use for LibreOffice-native document, spreadsheet, and presentation workflows or selected OpenDocument review comments.
---

# Edit OpenDocument Files

1. Use `$inspect-office-package` for every existing ODT/ODS/ODP. Preserve the uncompressed first `mimetype` entry and `META-INF/manifest.xml`.
2. Resolve the anchor against `content.xml` plus the relevant text, table/cell, draw/page, or annotation identity.
3. Use `odfpy` for supported creation and edits. For a localized edit in a complex file, patch the narrow XML subtree and preserve all other ZIP members.
4. Keep automatic and named style references stable. Preserve formulas, namespaces, RDF metadata, signatures, macros, embedded objects, tracked changes, annotations, and media unless the request owns them.
5. Recalculate ODS and render all formats with headless LibreOffice when available. Inspect the affected pages/slides/sheets.
6. Compare package parts with a narrow allowlist. Block rather than normalize unsupported features away.
7. Save ODF as canonical. An exported OOXML or PDF is a derived compatibility rendition, not a replacement unless the user asks for conversion.

Read [opendocument-package.md](references/opendocument-package.md) for ODF-specific rules.
