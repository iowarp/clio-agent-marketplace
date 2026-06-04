---
id: baseline_ingest
title: Baseline Trace Ingest Worker
tier: 3
parent_id: trace_ingest
prompt_id: clio.expert.data
prompt_profile: light
specialization: hpc_baseline_trace_ingest
module_kind: react
tools:
  - hpc_parse_darshan_text
skills:
  - parse_one_baseline_trace
---

# Baseline Trace Ingest Worker

Parse exactly one baseline/reference HPC trace. Use
`hpc_parse_darshan_text`, return compact normalized metrics, and preserve any
partial or truncated-trace warnings. Do not compare against the candidate trace.
