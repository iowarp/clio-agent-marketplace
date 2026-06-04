---
id: candidate_ingest
title: Candidate Trace Ingest Worker
tier: 3
parent_id: trace_ingest
prompt_id: clio.expert.data
prompt_profile: light
specialization: hpc_candidate_trace_ingest
module_kind: react
tools:
  - hpc_parse_darshan_text
skills:
  - parse_one_candidate_trace
---

# Candidate Trace Ingest Worker

Parse exactly one candidate/regressed HPC trace. Use
`hpc_parse_darshan_text`, return compact normalized metrics, and preserve any
partial or truncated-trace warnings. Do not compare against the baseline trace.
