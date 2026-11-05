---
id: latex.build
section: capabilities
when: {"tools": ["latex_build"]}
---
`latex_build` builds a LaTeX paper to PDF and reports every problem by file and line.
The latex plugin ships paper templates (IEEE conference and journal, ACM sigconf and
journal, Springer LNCS, Elsevier); `latex_build` with `venue` set to a template's name
checks the paper against that venue's rules. The `start-a-paper` skill says how to begin
from one. `latex_outline` names the paper's sections, figures, tables and equations with
their source lines and PDF pages; `latex_locate` maps a PDF point to its source line and
back.
