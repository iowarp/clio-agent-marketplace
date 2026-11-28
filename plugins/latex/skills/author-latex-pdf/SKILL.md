---
name: author-latex-pdf
description: Use for .tex sources and LaTeX-backed PDFs - creating or revising, building with latex_build, checking whether a paper is ready for a venue (its page limit, double-blind review, required packages, paper size), verifying, and mapping PDF review comments back to the source.
---

# Author LaTeX and PDF

- `.tex` and the files it includes are canonical; the compiled PDF is built from them.
- The document class, bibliography engine, custom commands, labels, citation keys and packages are the paper's own; changing them changes more than the request may intend.
- `latex_build(entry)` builds the paper, where `entry` is its main `.tex` file. Its folder is the project: `\input` files, the `.bib` and figures are found beside it. Each build reflects the sources as they are at that moment.
- The result lists problems, each with its kind, file and line. `status` is `failed` when the paper has an error, an undefined reference or citation, or a missing file, even if a PDF was made; a paper with those problems does not build cleanly.
- `missing_package` means a package could not be downloaded; it needs network access the first time. `shell_escape_unsupported` means the paper needs shell escape, which is never enabled; a package that does not need it, such as `listings` instead of `minted`, builds. `unsupported_bibliography_backend` means biblatex with biber; BibTeX builds.
- With `venue` set to a template's name, the build checks the paper against that venue's rules. Checks marked `to_check` need the person's judgement.
- `view_pdf` shows the affected pages: overflow, fonts, figures, equations and links.
- A figure drawn by a script and registered with `create_artifact(path=<figure>, used=[<script>, <data>])` carries its producer: a comment on that figure in the PDF names the script that made it. An unregistered figure's comment says its producer is unknown.
- `latex_outline` finds "Figure 3" or "Section 4.2" in the source; `latex_locate` maps a PDF place to its source, or a source line to where it lands.
- A build that makes a PDF makes the paper (the result's `paper`): one artifact named by the paper's `\title`, built from the versions of the source files it read. Each build after a change is its next version. The paper's card opens its sources and PDF together, and the person's comments on it name the source file and lines. The paper is known by its title; the PDF's file path is a build output, not the deliverable.

[latex-review.md](references/latex-review.md) covers review and tracked-source facts.
