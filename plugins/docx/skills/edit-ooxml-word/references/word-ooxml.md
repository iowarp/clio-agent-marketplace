# WordprocessingML edit notes

- Main content usually lives in `word/document.xml`; headers, footers, footnotes, endnotes, comments, text boxes, and glossary are separate stories.
- Text can be split across many `w:r`/`w:t` nodes. Match visible text with a reversible node map, then change only the minimum nodes.
- Preserve `xml:space="preserve"` when leading or trailing spaces matter.
- Relationships in `word/_rels` bind hyperlinks, images, charts, and embedded objects.
- Comments require range start/end markers in the story plus `word/comments.xml`; modern Word may also carry people/comment-extension parts.
- Tracked deletion uses `w:delText`, not ordinary `w:t`. Change metadata needs author, date, and stable IDs.
- Do not remove custom XML, macros, signatures, content controls, fields, bookmarks, or accessibility metadata because a high-level library does not expose them.
