---
name: edit-ooxml-presentation
description: Use to create or revise .pptx decks, or review selected slides and shapes, preserving layouts, masters, notes, media and comments for Microsoft PowerPoint.
---

# Edit OOXML Presentations

1. Preflight an existing deck with `$inspect-office-package`. Inventory masters, layouts, themes, notes, comments, charts, media, embedded objects, transitions, and animations.
2. When a comment entry's Source line names a slide and shapes (`slide 2, shape 4 "Chart 3"`), edit that shape by its ID on that slide. Position or visible text alone is not identity.
3. Use `python-pptx` for new decks and supported edits. For an existing sophisticated deck, prefer targeted slide XML edits; its unsupported features must not disappear on save.
4. Preserve theme-based formatting, placeholder bindings, crop/fill settings, alt text, notes, and relationship IDs. Do not flatten editable charts or diagrams into images unless explicitly requested.
5. Compare the package with only the affected slide/comment/media parts allowed.
6. Render through LibreOffice when available and visually inspect every changed slide plus representative title/content/closing slides. Check text overflow, cropping, z-order, font substitution, contrast, and speaker notes.
7. Save the real `.pptx` as canonical. PDF previews are derived and may not prove animations or transitions.

Read [presentation-ooxml.md](references/presentation-ooxml.md) before direct package editing.
