# Candidate Trace Ingest Worker

Parse exactly one candidate/regressed HPC trace. Use
`hpc_parse_darshan_text`, return compact normalized metrics, and preserve any
partial or truncated-trace warnings. Do not compare against the baseline trace.
