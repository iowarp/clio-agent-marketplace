# PresentationML invariants

- Slide order is in `ppt/presentation.xml`; each slide’s stable package identity follows its relationship, not the visible index.
- Shape IDs are local to a slide and can include placeholders, groups, charts, pictures, and graphic frames.
- Formatting may inherit from layout, master, theme, and placeholder. Inherited style converted into unrelated direct formatting no longer follows them.
- Notes slides, comments, authors, transitions, timing/animation, and media relationships are separate parts.
- SmartArt, embedded workbooks, charts, equations, and OLE objects require package preservation even when a library cannot edit them.
- A valid ZIP/XML package can still have clipped or displaced content in the editing view or the rendered slideshow.
