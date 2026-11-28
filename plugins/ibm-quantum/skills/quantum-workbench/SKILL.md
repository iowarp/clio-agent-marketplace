---
name: quantum-workbench
title: The quantum workbench
description: Use when the person wants the circuit, how it lands on a device and its results side by side in one place, linked so that selecting a gate shows where it runs, or wants a dashboard of a quantum experiment to keep or share. Triggers on "workbench", "show it all together", "dashboard of the runs", "where does this gate run".
keywords: [quantum, dashboard, workbench, views, level:L2]
---

# The quantum workbench

One surface holds three live views of the IBM Quantum connector: the circuit, the
same circuit on a device, and the results of the jobs that ran it. The circuit and
layout views share the selected gate: a gate the person selects in the circuit is
highlighted on the physical qubits that run it, and the other way round.

- `references/quantum-workbench.json` holds the surface's components. Its `<…>`
  placeholders take the circuit as OpenQASM 3 (the same text in both views), its
  blocks (`{name, start, end}` in gate order, end excluded), the device the layout is
  for (the backend of the noisy or hardware job), and the job ids with a label each
  (the reference first). Its `state` channels are what link the views.
- `create_a2ui_surface` (`components` from the file) publishes it, and
  `capture_a2ui_surface` shows what each view rendered.
- `/quantum/selected_gate` in the data model points at a gate: `{"index": <gate
  index>}` at that path highlights it in both views.

A live view runs only while the connector does. A `clio.chart.v1` beside the results
view, bound to the compared values (a table artifact written from `compare_jobs`),
keeps the comparison readable as a still chart after the connector stops.
