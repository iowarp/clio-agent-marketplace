# LaTeX review notes

- A generated PDF is rebuilt from its source; an edit made only to the PDF is lost at the next build.
- `\label` values and citation keys are the identities other text refers to; changing them breaks those references.
- Compiler shell escape is disabled; `latex_build` does not enable it.
- External URLs may be references; compilation does not fetch or execute them.
- A clean process exit is insufficient: logs show undefined references, missing citations, overfull boxes affecting the reviewed layout, and absent assets.
- A PDF quad identifies appearance, not source identity; quote text and the recorded source map identify the source.
