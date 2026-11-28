---
name: edit-ooxml-presentation
description: Use to create or revise .pptx decks, or review selected slides and shapes, preserving layouts, masters, notes, media and comments for Microsoft PowerPoint.
---

# Edit OOXML Presentations

- `$inspect-office-package` inventories an existing deck's masters, layouts, themes, notes, comments, charts, media, embedded objects, transitions, and animations, and compares the package after an edit.
- A comment entry's Source line names a slide and shapes (`slide 2, shape 4 "Chart 3"`); the shape's ID on that slide is its identity. Position or visible text alone is not identity.
- `python-pptx` handles new decks and the edits it supports. Targeted slide XML edits keep an existing sophisticated deck's unsupported features, which a library save can drop.
- Theme-based formatting, placeholder bindings, crop/fill settings, alt text, notes, and relationship IDs are part of the deck. Editable charts or diagrams flattened into images are no longer editable.
- A package comparison that allows only the affected slide/comment/media parts shows any other drift.
- A LibreOffice render shows changed slides and representative title/content/closing slides: text overflow, cropping, z-order, font substitution, contrast, and speaker notes.
- The real `.pptx` is canonical. PDF previews are derived and may not show animations or transitions.

[presentation-ooxml.md](references/presentation-ooxml.md) covers PresentationML for direct package editing.
