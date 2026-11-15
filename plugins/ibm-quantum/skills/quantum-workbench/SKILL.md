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

1. Load `references/quantum-workbench.json`. It is the surface's components.
2. Fill every `<…>`: the circuit as OpenQASM 3 (the same text in both views), its
   blocks (`{name, start, end}` in gate order, end excluded), the device the layout
   is for (the backend of the noisy or hardware job), and the job ids with a label
   each (the reference first). Keep the `state` channels as they are.
3. Publish it with `create_a2ui_surface` (`components` from the file), then check it
   with `capture_a2ui_surface` and say what each view shows.
4. Use `/quantum/selected_gate` to point the person at a gate: update the data model
   at that path with `{"index": <gate index>}` and both views highlight it.

A live view runs only while the connector does. For a dashboard that should still
show something after the connector stops, add a `clio.chart.v1` beside the results
view, bound to the compared values (a table artifact you write from
`compare_jobs`), so the comparison stays readable as a still chart.
