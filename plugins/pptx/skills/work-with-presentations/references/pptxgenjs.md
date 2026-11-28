# JavaScript slides with PptxGenJS

`prepare_document_runtime` returns the command and package version. The managed
stack currently locks `pptxgenjs` 4.0.1. A builder saved in its returned
JavaScript workspace resolves the package and runs with `javascript.script_argv`.
PptxGenJS creates new decks; it does not import an existing presentation for
editing.

`examples/create-reference-deck.mjs` is a complete runnable reference: six
themed slides with an editable native chart, tables, source captions and
speaker notes. Run from the prepared JavaScript workspace with an absolute
output-directory argument, it writes a PPTX and explicitly fictional source data
without changing user files. Its rendered slides show what it looks like as a
visual reference. Its slide count and fictional content are not a template for
every task.

Slide coordinates and dimensions use inches; font sizes use points. `LAYOUT_WIDE`
is approximately 13.33 × 7.5 inches. An explicit layout and font theme, with
shared colours and margins, keep slides consistent. A master suits common footer
or background objects; it also pushes every slide toward the same composition.

This runnable library example shows a theme, editable text and table, and notes.
Its one-slide content is a capability check, not a finished presentation.

```javascript
import pptxgen from 'pptxgenjs';

const deck = new pptxgen();
deck.layout = 'LAYOUT_WIDE';
deck.title = 'Evidence review';
deck.subject = 'Source-supported meeting presentation';
deck.theme = { headFontFace: 'Arial', bodyFontFace: 'Arial', lang: 'en-US' };
const colours = { ink: '202124', accent: '244C62', muted: '60666D', paper: 'FFFFFF' };
const slide = deck.addSlide();
slide.background = { color: colours.paper };
slide.addText('What the evidence establishes', {
  x: 0.65, y: 0.5, w: 12.0, h: 0.65, fontSize: 32,
  bold: true, color: colours.ink, margin: 0, breakLine: false,
});
slide.addText('Replace this example with a specific, source-supported finding.', {
  x: 0.65, y: 1.45, w: 11.9, h: 0.8, fontSize: 22,
  color: colours.ink, margin: 0, valign: 'top',
});
slide.addTable([
  [{ text: 'Evidence', options: { bold: true } }, { text: 'Limitation', options: { bold: true } }],
  ['Source identifier and observation', 'Material uncertainty from the source'],
], {
  x: 0.65, y: 2.65, w: 12.0, colW: [6, 6], rowH: 0.65,
  fontFace: 'Arial', fontSize: 20, color: colours.ink,
  margin: 0.14, border: { type: 'solid', color: 'D7DDE1', pt: 0.6 },
});
slide.addText('Source: identify the supplied evidence; preserve its units.', {
  x: 0.65, y: 6.7, w: 11.8, h: 0.3, fontSize: 12,
  color: colours.muted, margin: 0,
});
slide.addNotes('Explain the finding, source, uncertainty and presenter context here.');
await deck.writeFile({ fileName: process.argv[2] ?? 'evidence-review.pptx' });
```

For a source figure, `deck.imageSizingContain(path, x, y, w, h)` passed to
`slide.addImage({ path, ...sizing })` preserves aspect ratio inside the allotted
box. `imageSizingCrop` crops; a crop through chart axes, legends or evidence
removes part of the evidence.

Native text objects with their `bullet` options make real bullets; a literal
bullet glyph is plain text. Text bounds do not guarantee rendered fit. Automatic
shrink-to-fit resolves overflow by giving up legibility; shortening or splitting
the content keeps it. Notes suit references and supporting context; an essential
limitation is seen only when it is on the slide.

Official references:
- https://gitbrent.github.io/PptxGenJS/docs/usage-pres-options.html
- https://gitbrent.github.io/PptxGenJS/docs/api-images/
- https://gitbrent.github.io/PptxGenJS/docs/speaker-notes/
