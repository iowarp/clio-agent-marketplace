---
id: earthscope-gnss.answer-format
section: domain
---
## Writing the final answer

Your `answer` is human-readable markdown PROSE ONLY (sentences, bullets, at most
one small table), starting with the heading "## Region". NEVER put JSON in it: no
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
be the SAME station. Paths are copied whole as single absolute strings — CSV =
exactly `acquisition.local_path`, PNG = exactly `artifact.path` (never doubled,
never rebuilt by joining a directory + filename).
