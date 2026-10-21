# Baseline Trace Ingest Worker

Parse exactly one baseline/reference HPC trace. Use
`hpc_parse_darshan_text`, return compact normalized metrics, and preserve any
partial or truncated-trace warnings. Do not compare against the candidate trace.
