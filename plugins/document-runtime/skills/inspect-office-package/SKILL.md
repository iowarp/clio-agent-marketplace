---
name: inspect-office-package
description: Inventories and compares .docx, .xlsx, .pptx, .odt, .ods or .odp packages around an edit, so unknown parts, macros, comments and tracked changes survive.
---

# Inspect Office Package

The comparison matters most for files created outside CLIO, whose parts a library may not own.

- `scripts/package_guard.py inventory INPUT --output before.json` records the package before an edit.
- An edit method is expected to change specific package parts; [part-ownership.md](references/part-ownership.md) lists typical scopes.
- Present features a library cannot round-trip—macros, signatures, ActiveX, embedded objects, custom XML, advanced chart/workbook/presentation features—survive a targeted ZIP/XML mutation; otherwise the edit is a typed incompatibility.
- After an edit, the comparison is:

   `scripts/package_guard.py compare before.json OUTPUT --allow 'word/document.xml' --allow 'docProps/core.xml'`

- A removed, added, or unexpectedly changed part outside the allowlist is drift the edit caused. An allowlist entry is justified by the requested edit and format semantics for that exact part.
- LibreOffice, when available, opens, recalculates or renders the real result. Package parity is necessary but not sufficient.

Unzip-and-rezip is not a neutral normalization: package metadata, relationship integrity, and untouched compressed parts are part of compatibility.
