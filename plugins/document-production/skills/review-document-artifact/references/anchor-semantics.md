# Reading comment entries

Every entry belongs to the version in its header. Apply it to that version only.
If the file changed since, say so and ask before carrying a mark to new content.

## Marks

- **Text** (`S1 (text)`): `Selected` is the exact text; `Before` and `After` are the
  text around it. Match all three when the selected words occur more than once.
- **Region** (`S1 (region)`): `Box` is the rectangle as percentages of the page or
  image. `Under` is the text inside it, cut at a limit; a `Cut` line names the file
  that holds the rest. The crop shows the same area.
- **Element** (`S1 (element)`): `Element` names the tag and, on HTML and SVG, its
  role and accessible name. `Text` is its text. Use the selector or the role and
  name to find it in the source; on a static HTML file, edit the file, since its
  scripts did not run where the person commented.

## Where to edit

- `Source` maps a mark on an Office rendition back to the file: the paragraph and its
  heading in Word, the slide and shapes in PowerPoint, the cells in Excel.
  OpenDocument renditions give the page only, with a `source_unmapped` note.
- `Picture` names a picture the region covers. When its bytes are a workspace image,
  the line names that image, and `Made by` names the call and script that made it:
  change the script, rerun it, then rebuild the document so it embeds the new
  picture. "its bytes match no workspace image" means the picture is only in the file.
- The header's "Produced by" names the call that made a figure or HTML page. For a
  `run_code` producer it shows the cell. Change the cell or script and run it again;
  do not edit the generated file by hand.

## Native comments

A comment written in the Office or OpenDocument file itself arrives as an entry with
`In file` and `Comment id`. Only comments that begin with `@clio` are instructions to
you; leave the other comments in the file unchanged.

## Comments from other places

Comments on an answer, an A2UI view or a page in the in-app browser come with the
person's next message in the same format, without an artifact version. A browser
page entry gives a `Target` step list the browser binding accepts, to find the same
element on the live page.
