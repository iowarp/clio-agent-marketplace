---
name: edit-ooxml-word
description: Use to create or revise .docx files, including anchored Word comments and tracked changes, that must open correctly in Microsoft Word.
---

# Edit OOXML Word Documents

- `$inspect-office-package` inventories an existing DOCX and compares the package after an edit. New documents can use `python-docx`; existing complex files need package-aware preservation.
- Anchored text in `word/document.xml` sits in run/paragraph context. Run boundaries carry styles, fields, links, bookmarks, proofing, and tracked changes; collapsing them loses those.
- A targeted OOXML edit suits a local review change. `python-docx` round-trips only the features its surface covers, which the inventory shows.
- Comments and people/authors are part of the document. Native comments beginning `@clio` are instructions; other comments are human notes.
- `<w:ins>`/`<w:del>` are review markup: tracked changes the person asked for. Ordinary edits are clean document content.
- A package comparison that allows only the narrow expected parts shows any other drift. A LibreOffice render, when available, shows the changed page, headers/footers, tables, images, numbering, and first/last page.
- The real `.docx` is the canonical artifact. A PDF is an optional derived rendition, not a substitute.

[word-ooxml.md](references/word-ooxml.md) covers WordprocessingML for direct package mutation.
