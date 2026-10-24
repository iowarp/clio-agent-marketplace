---
name: edit-ooxml-word
description: Create or revise Office-compatible DOCX files, including comments and requested tracked changes, while preserving unknown OOXML parts. Use for .docx creation, anchored Word review comments, or edits that must open correctly in Microsoft Word.
---

# Edit OOXML Word Documents

1. Run `$inspect-office-package` before editing an existing DOCX. New documents may use `python-docx`; existing complex files require package-aware preservation.
2. Locate anchored text in `word/document.xml` with surrounding run/paragraph context. Do not collapse run boundaries blindly: they carry styles, fields, links, bookmarks, proofing, and tracked changes.
3. Prefer a targeted OOXML edit for a local review change. Use `python-docx` only when its round-trip surface covers the file’s inventoried features.
4. Preserve comments and people/authors. Native comments beginning `@clio` are instructions; other comments stay intact as human notes.
5. Emit `<w:ins>`/`<w:del>` only when the user requests tracked changes or the workflow explicitly requires review markup. Ordinary edits become clean document content.
6. Run the package guard again with the narrow expected parts, then open/render through LibreOffice when available. Inspect the changed page, headers/footers, tables, images, numbering, and first/last page.
7. Save a real `.docx` as the canonical artifact. A PDF is an optional derived rendition, never a substitute.

Read [word-ooxml.md](references/word-ooxml.md) before direct package mutation.
