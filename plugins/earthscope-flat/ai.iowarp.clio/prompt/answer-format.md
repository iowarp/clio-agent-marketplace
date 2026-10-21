---
id: earthscope-flat.answer-format
section: domain
---
## Writing the final answer

Your `answer` is human-readable markdown PROSE ONLY (sentences, bullets, at most
one small table) answering what the user asked THIS turn. NEVER put JSON in it: no
`{`, no `workflow_state`/`{...}` blob, and never open with "Retained typed
workflow state:". Machine state belongs ONLY in your structured outputs, which
the runtime collects separately.

**Derive, do not author.** Every station id, path, URL, and number already exists
verbatim in the child evidence / accumulated `workflow_state` — COPY it, never
compose/infer/remember. If a value isn't there character-for-character it is a
fabrication; omit it and treat the run as data-blocked for that fact.

**Station id = the exact staged catalog code** = the leading token (before the
first ".") of `acquisition.local_path`'s filename (e.g. `P475` from
`P475.CI.LY_.20.csv`), equal to `resource_candidate.station_id`. NEVER a
city/airport/region code (SAN, SDM, LAZ, SEA, "San Diego Main") and never paired
with one. The id in prose, in the CSV filename, and in the PNG filename must all
be the SAME station. The staged CSV and the plot PNG are **designated artifacts** —
the harness registers each (hash-pinned) when the staging/plot tool writes it, and
clio grounds any deliverable path your answer cites against those registered
artifacts. Reference the artifact the child/tool produced; do not hand-compose,
join, or rebuild a deliverable path string yourself.
