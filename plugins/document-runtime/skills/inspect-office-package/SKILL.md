---
name: inspect-office-package
description: Inventory and compare OOXML or OpenDocument ZIP packages so edits preserve unknown parts, relationships, macros, comments, tracked changes, media, and metadata. Use before and after any agent edit to .docx, .xlsx, .pptx, .odt, .ods, or .odp, especially files created outside CLIO.
---

# Inspect Office Package

1. Run `scripts/package_guard.py inventory INPUT --output before.json`.
2. Identify the exact package parts the chosen edit method is expected to change. Review [part-ownership.md](references/part-ownership.md).
3. If the library cannot round-trip present features—macros, signatures, ActiveX, embedded objects, custom XML, advanced chart/workbook/presentation features—use targeted ZIP/XML mutation or stop with a typed incompatibility.
4. After editing, run:

   `scripts/package_guard.py compare before.json OUTPUT --allow 'word/document.xml' --allow 'docProps/core.xml'`

5. Every removed, added, or unexpectedly changed part is a failure. Expand the allowlist only when the requested edit and format semantics justify that exact part.
6. Open/recalculate/render with LibreOffice when available and inspect the real result. Package parity is necessary but not sufficient.

Never use unzip-and-rezip as a casual normalization step: package metadata, relationship integrity, and untouched compressed parts are part of compatibility.
