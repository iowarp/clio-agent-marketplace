# WordprocessingML edit notes

- Main content usually lives in `word/document.xml`; headers, footers, footnotes, endnotes, comments, text boxes, and glossary are separate stories.
- Text can be split across many `w:r`/`w:t` nodes. A reversible node map matches visible text; changing only the minimum nodes keeps the rest intact.
- `xml:space="preserve"` keeps leading or trailing spaces.
- Relationships in `word/_rels` bind hyperlinks, images, charts, and embedded objects.
- Comments require range start/end markers in the story plus `word/comments.xml`; modern Word may also carry people/comment-extension parts.
- Tracked deletion uses `w:delText`, not ordinary `w:t`. Change metadata needs author, date, and stable IDs.
- Custom XML, macros, signatures, content controls, fields, bookmarks, and accessibility metadata are part of the document even when a high-level library does not expose them.
