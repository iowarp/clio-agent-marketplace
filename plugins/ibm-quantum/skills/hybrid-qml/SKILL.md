---
name: hybrid-qml
title: Hybrid quantum-classical models
description: Use when the person wants a quantum layer inside a machine-learning model (a hybrid quantum-classical classifier or regressor, a quantum neural network, a variational classifier), to train it, compare it with a classical model, or see how hardware noise changes its predictions. Triggers on "hybrid quantum classifier", "quantum neural network", "EstimatorQNN", "TorchConnector", "quantum machine learning", "how does noise change the classifier".
keywords: [quantum, quantum-machine-learning, pytorch, qiskit-machine-learning, classifier, level:L2]
---

# Hybrid quantum-classical models

A small classical network reduces the input to a few features, a parameterized
circuit maps them to an expectation value, and the model trains end to end. The
quantum part is small on purpose: today's devices are noisy, so the comparison
that matters is the same model on exact simulation, on a noisy simulation of a
device, and on the device.

## 1. Build the model and its baseline

- Write the model in PyTorch with Qiskit Machine Learning: a feature map
  (`zz_feature_map(n)`) then an ansatz (`real_amplitudes(n, reps=1)`), wrapped by
  `EstimatorQNN` with the input parameters and the weight parameters named, and
  `TorchConnector` as the layer. Train on `StatevectorEstimator`.
- Always train a classical baseline on the same features beside it (a linear layer
  where the quantum layer is), with the same data, epochs and optimizer. Report both.
- Install what the script needs into the environment `run_code` uses (CPU builds of
  `torch` and `torchvision`, `qiskit-machine-learning`), and keep datasets in the
  workspace's cache folder so a rerun does not download them again.

## 2. Train in the background and show it live

The person watches both models learn while training runs, so the dashboard exists
before the first epoch ends:

1. `open_stream("qml-training")` and keep its `view_uri`.
2. Load `references/training-dashboard.json`, put the `view_uri` in its two charts and
   the task in its scope line, and publish it with `create_a2ui_surface`. Its two
   `trajectories` charts follow the stream: loss and training accuracy over `epoch`, one
   line per `model`.
3. Start the training as below.

`run_code`'s kernel is CLIO's own Python: it has the stream and task bindings, but not
the packages you installed for the model. So the training script runs in the
environment that has them, prints one JSON line per model per epoch, and a background
`run_code(background=True, label=...)` starts it, writes each line to the stream and
wakes the conversation at the end:

```python
import asyncio, json
s = await stream.open("qml-training", window=500)     # the stream the dashboard follows
proc = await asyncio.create_subprocess_exec(
    PYTHON, "train.py",                             # the environment with torch and qiskit
    stdout=asyncio.subprocess.PIPE, cwd=WORKSPACE)
async for line in proc.stdout:
    try:
        row = json.loads(line)                      # {"epoch", "model", "loss", "train_acc"}
    except ValueError:
        continue
    await s.write(**row)
code = await proc.wait()
await task.notify("Training finished" if code == 0 else f"Training failed ({code})")
```

The training script saves the trained weights and the test features to the workspace,
for the evaluation below.

Do not poll the task; the notification wakes you.

## 3. Evaluate on three backends, one job each

- Compute the test inputs' features in `run_code` with the trained classical part,
  and form one parameter set per input: the features in the order of the circuit's
  input parameters, then the trained weights in the order of its weight parameters.
  Check the order against `circuit.parameters` (sorted by name) in the script.
- Write the circuit out as OpenQASM 3 in standard gates (transpile to
  `["h", "p", "cx", "ry", "rz"]` before `qasm3.dumps`) so the server can read it.
- Call `run_estimator` once on `local_exact` and once on a `fake_<device>`, each with
  all the parameter sets in `parameter_values` and the model's observable (for a
  two-qubit model, `"ZZ"`). With a key and the person's go-ahead, a third call on a
  real device, after the `ibm-quantum-budget` checks.
- `view_circuit` with the feature map and the ansatz as `blocks`; `view_layout` for
  the noisy job; `view_results` with the jobs and the true labels as `expected`.
- `compare_jobs` with `expected` gives accuracy per job and the inputs whose class
  flipped under noise. Use the threshold the model's output uses (an expectation
  value at or above 0 is class 1 unless the model maps it otherwise).

## 4. Report honestly

- Give the hybrid model's and the baseline's accuracy on each backend, and name the
  job ids.
- Say what the result does and does not show: a two-class task on a reduced dataset
  is easy for both models, so equal accuracy is expected and is not evidence of a
  quantum advantage. What the comparison shows is how much the device's noise moves
  the expectation values and which inputs sit near the decision boundary.
- When asked why one input flipped, answer from the selected parameter set in the
  results view (its exact and noisy values and how close it is to the threshold) and
  from the layout (the two-qubit gates and swaps the device added), not from general
  text.

## 5. Keep it as a study

The comparison is a small study, recorded with the science log (`run-a-study`) so
it can be read, compared and extended later:

- A `question` entry: how the device's noise changes this classifier's predictions.
- An `experiment` entry: the trained model, the test inputs and the backends.
- One `observation` per evaluation job, citing its `run_estimator` call in
  `from_calls`, with the job's accuracy, the mean shift from the exact values and the
  number of flipped inputs as `measurements` (`conditions`: the backend).
- An `evidence` entry for what the comparison supports, with its honest `strength`.
