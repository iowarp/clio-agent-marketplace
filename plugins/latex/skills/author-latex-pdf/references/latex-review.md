# LaTeX review rules

- Never edit only a generated PDF when a source artifact is available.
- Retain `\label` values and citation keys unless changing identity is explicit.
- Treat compiler shell escape as disabled. Do not enable it to make a document compile.
- External URLs may be references, but compilation must not fetch or execute them.
- A clean process exit is insufficient: scan logs for undefined references, missing citations, overfull boxes affecting the reviewed layout, and absent assets.
- A PDF quad identifies appearance, not source identity; combine it with quote text and recorded source map.
