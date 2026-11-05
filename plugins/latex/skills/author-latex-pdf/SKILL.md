---
name: author-latex-pdf
description: Use for .tex sources and LaTeX-backed PDFs - creating or revising, building with latex_build, verifying, and mapping PDF review comments back to the source.
---

# Author LaTeX and PDF

1. Treat `.tex` and the files it includes as canonical; the compiled PDF is built from them.
2. Preserve the document class, bibliography engine, custom commands, labels, citation keys and packages unless the request requires changing them.
3. Build with `latex_build(entry)`, where `entry` is the paper's main `.tex` file. Its folder is the project: `\input` files, the `.bib` and figures are found beside it. Build early, and again after each change.
4. Read the result's problems, each with its kind, file and line. `status` is `failed` when the paper has an error, an undefined reference or citation, or a missing file, even if a PDF was made. Fix those before saying the paper builds.
5. `missing_package` and `shell_escape_unsupported` are reported as written: a package that could not be downloaded needs network access the first time, and shell escape is never enabled (use a package that does not need it, such as `listings` instead of `minted`). `unsupported_bibliography_backend` means biblatex with biber; offer to switch the paper to BibTeX.
6. For a venue, build with `venue` set to the template's name and fix every failed check. Checks marked `to_check` need the person's judgement; name them.
7. Look at the affected pages with `view_pdf`; check overflow, fonts, figures, equations and links.
8. To find "Figure 3" or "Section 4.2" in the source, use `latex_outline`; to find what a PDF place is in the source, or where a source line lands, use `latex_locate`.
9. A build that makes a PDF makes the paper (the result's `paper`): one artifact named by the paper's `\title`, built from the versions of the source files it read. Each build after a change is its next version. The reply ends with the paper's card, which opens its sources and PDF together, and the person's comments on it name the source file and lines. Refer to the paper by its title; the PDF's file path is a build output, not the deliverable.

Read [latex-review.md](references/latex-review.md) for review and tracked-source rules.
