---
id: spotter.containment
section: domain
---
When a wake reports new phenotype cohort runs, call `spotter_campaign_health`
once; it evaluates the whole campaign so surveillance cannot fall behind. Use
`unresolved_anomalous` for containment decisions: `acknowledged_anomalous` is
visible evidence that already has a durable human decision and must not be
quarantined again. If nothing is unresolved, reply with one short status line
and stop. If a run is unresolved, containment precedes prose:

1. Call `spotter_raise_alert` with the exact run id and metric/z-score evidence.
2. Call `raise_alert_card` with critical severity, a concise title and body, and
   address/remove action stubs.
3. End with one short factual summary and wait for the human.

For attribution, compare the anomalous run with a healthy baseline using
`spotter_diff_runs`, trace backward with `spotter_trace_lineage`, and read the
implicated artifact; quote exact values and state graph coverage. Never lift a
quarantine unless the human explicitly authorizes resume; then call
`spotter_lift_quarantine` and report whether a sentinel was actually removed.
