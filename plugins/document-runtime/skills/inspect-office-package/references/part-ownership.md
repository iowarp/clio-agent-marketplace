# Office package part ownership

OOXML and ODF are ZIP packages containing XML plus binary assets. A high-level library generally owns only a subset.

Always inventory:

- part name, uncompressed size, CRC32, and SHA-256;
- relationship files and content-type declarations;
- VBA/macros, signatures, ActiveX, embedded OLE/packages, custom XML;
- comments, people/authors, tracked changes, notes, and threaded comments;
- styles, themes, numbering, shared strings, calculation chain/properties;
- drawings, media, charts, diagrams, transitions, and speaker notes.

Examples of expected edit scopes:

- Word paragraph text: `word/document.xml`; possibly numbering/styles only if explicitly changed.
- Spreadsheet cell value: worksheet part; shared strings or styles when applicable; calculation properties when recalculated.
- Presentation shape text: the exact slide part; related notes/layout/theme parts should not drift.
- ODF content edit: `content.xml`; style or manifest parts only when deliberately affected.

If a high-level save changes unrelated parts, do not bless the drift. Use a narrower package patch or block the edit.
