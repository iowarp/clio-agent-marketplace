---
id: factorio-flat.consultations
section: domain
---
When the scientist explicitly requests specialist consultations, load
`coordinate-scientific-work` and its relevant lifecycle reference before
starting any subagent. Start each requested independent consultation exactly
once in one parallel group. Once task ids are returned, keep those identities
through observe, wait and collect; never create replacement or duplicate tasks
for the same assignments after a skill load, an observation, a queue delay, a
subagent question or context compaction.
