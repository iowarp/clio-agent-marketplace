# Edit an existing PowerPoint with python-pptx

This uses the prepared Python runtime. Reading and rendering the source deck
shows its text hierarchy and object types. A revision saved to a new path leaves
the source file unchanged.

## Preserve text formatting

`shape.text = ...` and `paragraph.text = ...` replace the text frame's runs.
They can lose explicit font sizes, colours, emphasis and hyperlinks even when
the same text fits inside the original shape. Changing `run.text`, when the
target text belongs to that run, keeps its formatting attached to the existing
run.

This prints paragraph and run boundaries:

```python
from pptx import Presentation

deck = Presentation(source_path)
for shape in deck.slides[-1].shapes:
    if shape.has_text_frame:
        for paragraph in shape.text_frame.paragraphs:
            print([(run.text, run.font.size, run.font.bold)
                   for run in paragraph.runs])
```

For a template whose exact target occupies one run, this bounded edit preserves
the existing run. It raises unless exactly one run matches, so the wrong shape
is not edited silently and a missed replacement is visible:

```python
from pptx.slide import Slide

def replace_single_run(slide: Slide, old: str, new: str) -> None:
    """Replace one exact run while retaining its formatting properties."""
    matches = [run for shape in slide.shapes if shape.has_text_frame
               for paragraph in shape.text_frame.paragraphs
               for run in paragraph.runs if run.text == old]
    if len(matches) != 1:
        raise ValueError(f"Expected one exact text run for {old!r}")
    matches[0].text = new

replace_single_run(deck.slides[-1], "Check calibration",
                   "Request calibration records")
deck.save(output_path)
```

Text spanning several differently formatted runs needs an explicit replacement
mapping that preserves those boundaries; concatenated into a new plain paragraph,
it loses them. A rebuilt paragraph keeps its look only when its paragraph and run
properties, links, bullets, alignment and spacing are copied. A font property
of `None` means inherited formatting, not an unset size.

## Keep objects and notes intact

Charts stay native and tables editable when edited in place; an unchanged slide
recreated as a picture loses both. Table-cell text edited through its existing
runs keeps its formatting. Notes can hold supporting references and caveats
outside the requested change.

Reopening the saved deck shows slide count, object types, changed text and
notes to compare against the source. The rendered overview sheets show the
changed slide's hierarchy, line wrapping, contrast and margins; individual slides
resolve what the overview leaves open. Structural preservation does not prove
the new text fits. A correction in the native file shows only in a new render.
