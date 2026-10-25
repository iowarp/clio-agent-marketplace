# PresentationML invariants

- Slide order is in `ppt/presentation.xml`; each slide’s stable package identity follows its relationship, not the visible index.
- Shape IDs are local to a slide and can include placeholders, groups, charts, pictures, and graphic frames.
- Formatting may inherit from layout, master, theme, and placeholder. Avoid converting inherited style into unrelated direct formatting.
- Notes slides, comments, authors, transitions, timing/animation, and media relationships are separate parts.
- SmartArt, embedded workbooks, charts, equations, and OLE objects require package preservation even when a library cannot edit them.
- Validate both editing view and rendered slideshow appearance; a valid ZIP/XML package can still have clipped or displaced content.
