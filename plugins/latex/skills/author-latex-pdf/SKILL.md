---
name: author-latex-pdf
description: Create or revise LaTeX source, compile it locally to PDF, map PDF review selections back to source, and verify logs and rendered pages. Use for .tex sources, LaTeX-backed PDFs, mathematical or publication documents, and PDF review comments with source lineage.
---

# Author LaTeX and PDF

1. Treat `.tex` and included local sources as canonical; treat the compiled PDF as a derived rendition.
2. Resolve a PDF selection through recorded source mapping when available. Otherwise use the exact quote plus nearby structure and report ambiguity.
3. Preserve document class, bibliography engine, custom commands, labels, citations, and package versions unless the request requires changing them.
4. Compile with `scripts/render_latex.py SOURCE.tex OUTPUT_DIR`. It uses pinned local Tectonic behavior and never downloads arbitrary packages on the model’s instruction.
5. Fail on compilation errors, missing citations/references, or requested content absent from the PDF. Do not claim success from a `.tex` parse alone.
6. Visually inspect the affected page and representative first/last pages; check overflow, fonts, figures, equations, and hyperlinks.
7. Save source changes first, then the PDF rendition, preserving lineage from PDF to exact source revision.

Read [latex-review.md](references/latex-review.md) for review and tracked-source rules.
