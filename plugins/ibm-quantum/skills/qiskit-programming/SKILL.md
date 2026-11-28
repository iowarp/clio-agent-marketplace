---
name: qiskit-programming
title: Qiskit programs on IBM Quantum
description: Use for any quantum circuit work - building, simulating, transpiling or running a circuit -, since the connector already runs Qiskit and its simulators with nothing to install, keeps every run as a job and shows it in a view; also to compare backends or understand a result or a device. Triggers on "quantum circuit", "qubit", "Bell state", "GHZ", "run this on a quantum computer", "Qiskit", "simulate with noise", "why did this swap appear".
keywords: [quantum, qiskit, circuits, simulation, transpile, sampler, estimator, level:L2]
---

# Qiskit programs on IBM Quantum

The circuits and the classical code around them are Qiskit 2.x code or OpenQASM 3,
written in the conversation. The connector runs them, keeps every run as a job, and shows
circuits, layouts, results and devices in views the person can work in.

## Where a circuit runs

Every run tool takes `backend_name`, and only the last kind needs an account:

| `backend_name` | What runs | Use it for |
| --- | --- | --- |
| `local_exact` | Exact statevector results; Estimator values have no shot noise | The truth to compare against |
| `local_aer` (the default) | Ideal shots on this machine | Shot statistics without noise |
| `fake_<device>` | That device's noise, coupling map and basis gates, transpiled as the device would be | What hardware would do; `list_backends` gives the default fake device |
| any other name | The real device | Spends the person's quantum time; see `ibm-quantum-budget` |

Each kind checks the next: exact, then ideal shots, then a fake device. Hardware runs
spend the person's quantum time, so they happen only when the person asks for them.

## Build and run

- Circuits are OpenQASM 3 with `include "stdgates.inc";`, named parameters and
  a `bit` register for measurements. Parameters are bound in the order of
  `circuit.parameters`, which Qiskit sorts by name; the tool's error states the order
  when it is wrong, and a guessed order binds the wrong values.
- `run_sampler` counts bitstrings of a measured circuit. `run_estimator` takes
  `observables` (a Pauli string such as `"ZZ"`, the rightmost letter is qubit 0; a
  list of strings for one value each; or a weighted sum `[["ZZ", 0.5], ["XX", -0.5]]`)
  and removes final measurements itself.
- A batch of inputs is one call and one job: `parameter_values` as a list of
  parameter sets; one call per input makes one job per input.
- Every run returns a `job_id`; local ids start with `local-`. A local job usually
  returns its results in the same call; otherwise `get_job_results`.
  `list_my_jobs` lists local jobs first.
- A `fake_<device>` or hardware run is transpiled with the preset pass manager at
  `optimization_level` (default 1). Its result carries the two-qubit gate count and
  the layout, which explain a noisy result.
- A run you made in a script with the Qiskit SDK on a simulator can join the
  comparisons: `record_job` with the circuit and its counts or values gives it a
  `local-` id.

## Compare, then claim

`compare_jobs` lines up jobs that ran the same circuit: probabilities per bitstring
and the total variation distance for Sampler jobs; values per parameter set and
their differences for Estimator jobs, with accuracy and flipped sets when you give
`expected` labels. A claim about noise rests on those numbers and the jobs they came
from.

## Views

- `view_circuit` shows a circuit, with `blocks` naming its parts
  (`{name, start, end}` in gate order, end excluded).
- `view_layout` shows a circuit run on a device or a fake one: the physical qubits,
  the swaps routing added and the gate counts before and after, and the person can
  re-transpile at another level from the view.
- `view_results` shows a comparison, with the job ids and, for a classifier, the
  expected labels.
- `view_backend` shows a device and which qubits are good;
  `find_optimal_qubit_chains` ranks chains, and `view_layout` takes
  `initial_layout` to place a circuit on them.

What the person selects in a view is in your next turn's context (the gate, the
physical qubit or coupling, the bitstring or the parameter set). A question about
"this gate" or "this swap" is about that selection and the view's data, not general
text. A mark the person draws on a view arrives with the gates, qubits or
couplings under it.

## Look things up

`search_docs` and `get_page` read the Qiskit documentation; `lookup_error_code`
explains an IBM Quantum error code; the documentation beats a guessed API.
