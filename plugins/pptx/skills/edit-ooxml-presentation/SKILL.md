---
name: edit-ooxml-presentation
description: Create or revise Office-compatible PPTX decks while preserving slide identity, layouts, masters, themes, notes, media, animations, and comments. Use for .pptx creation, selected slide/shape review, or presentation deliverables that must open in Microsoft PowerPoint.
---

# Edit OOXML Presentations

1. Preflight an existing deck with `$inspect-office-package`. Inventory masters, layouts, themes, notes, comments, charts, media, embedded objects, transitions, and animations.
2. Resolve a `slide-shape` anchor using the exact slide relationship and shape ID. Position or visible text alone is not identity.
3. Use `python-pptx` for new decks and supported edits. For an existing sophisticated deck, prefer targeted slide XML edits; its unsupported features must not disappear on save.
4. Preserve theme-based formatting, placeholder bindings, crop/fill settings, alt text, notes, and relationship IDs. Do not flatten editable charts or diagrams into images unless explicitly requested.
5. Compare the package with only the affected slide/comment/media parts allowed.
6. Render through LibreOffice when available and visually inspect every changed slide plus representative title/content/closing slides. Check text overflow, cropping, z-order, font substitution, contrast, and speaker notes.
7. Save the real `.pptx` as canonical. PDF previews are derived and may not prove animations or transitions.

Read [presentation-ooxml.md](references/presentation-ooxml.md) before direct package editing.
