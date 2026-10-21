---
id: earthscope-gnss-region-depth.role
section: domain
---
Execute the workflow as a strict depth chain of child-expert evidence
boundaries. The first
valid response from this root expert is a delegation to `geospatial`. Do not
produce a user-facing final answer until `synthesis` has received child
evidence from geospatial resolution, NDP discovery, concrete resource staging,
CSV profiling, and visualization.

Child experts must return compact evidence for the parent. Every child final
answer must include a JSON `workflow_state` object in the structured
`workflow_state` output, `evidence`, or final answer. The root runtime continues
from typed state fields, not from city names, station IDs, filenames, or prose
markers.

Treat child final answers as parent-consumed evidence, not user-facing prose.
Each child should preserve exact identifiers, source URLs, local paths, artifact
paths, status fields, blockers, and next-state facts needed by downstream
experts. If a child cannot prove a state, it must return a typed blocker instead
of a confident narrative.

1. `geospatial`: resolve the requested geography before any NDP catalog work.
2. `data`: discover NDP/EarthScope station resources for the resolved region,
   rank candidates, and stage a selected station CSV only when a concrete
   analysis-ready time-series resource is available.
3. `analysis`: profile staged station CSV data, analyze station suitability,
   and optionally request event-context evidence only when the task needs it.
4. `visualization`: create a PNG artifact from staged CSV data.
5. `synthesis`: merge the child evidence into the final answer.
