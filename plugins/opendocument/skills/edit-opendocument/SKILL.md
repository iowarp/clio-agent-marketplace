---
name: edit-opendocument
description: Use to create or revise ODT, ODS or ODP files natively, or apply OpenDocument review comments, preserving metadata, styles, formulas, comments and media.
---

# Edit OpenDocument Files

- `$inspect-office-package` inventories an existing ODT/ODS/ODP and compares it after an edit. The uncompressed first `mimetype` entry and `META-INF/manifest.xml` make the file a valid package.
- An anchor resolves against `content.xml` plus the relevant text, table/cell, draw/page, or annotation identity.
- `odfpy` handles supported creation and edits. A localized edit in a complex file can patch the narrow XML subtree and leave all other ZIP members as they were.
- Automatic and named style references stay stable only when untouched. Formulas, namespaces, RDF metadata, signatures, macros, embedded objects, tracked changes, annotations, and media are part of the file.
- Headless LibreOffice, when available, recalculates ODS and renders all formats, showing the affected pages/slides/sheets.
- A package comparison with a narrow allowlist shows drift. Normalizing unsupported features away removes them; an edit that would do so is blocked by that incompatibility.
- ODF is canonical. An exported OOXML or PDF is a derived compatibility rendition, not a replacement unless the person asked for conversion.
- `create_artifact` registers the ODF file. It gets a version-bound PDF preview for Clio's viewer automatically, kept in lineage rather than as another deliverable (`pdf_preview=false` omits it). Registering or listing that PDF separately makes it another deliverable. `pdf_previews` reports a missing converter, which leaves the source registered.

[opendocument-package.md](references/opendocument-package.md) covers ODF-specific package facts.
