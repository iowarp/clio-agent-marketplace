---
id: earthscope-gnss-region-depth.guidance-5
section: domain
---
Path integrity is mandatory for the root response. Copy local paths exactly as
returned by children and tools. Do not normalize, shorten, relocate, or
reconstruct paths. A path under the active workspace artifact root must not be
rewritten into a home-directory path, a process-local path, or a shorter
approximation.

If the workflow is complete, delegate once to `synthesis`, then answer normally.
Do not continue delegating after `synthesis` has produced a final brief with
artifact and provenance evidence.
