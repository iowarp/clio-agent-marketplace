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

## The model and its baseline

- The model is PyTorch with Qiskit Machine Learning: a feature map
  (`zz_feature_map(n)`) then an ansatz (`real_amplitudes(n, reps=1)`), wrapped by
  `EstimatorQNN` with the input parameters and the weight parameters named, and
  `TorchConnector` as the layer, trained on `StatevectorEstimator(default_precision=0.0)`:
  `EstimatorQNN`'s default estimator samples at a precision of 1/64, so training values
  and gradients would carry shot noise and the exact evaluation would not match the
  trained model.
- A hybrid result means something only next to a classical baseline on the same
  features (a linear layer where the quantum layer is), with the same data, epochs and
  optimizer.
- The model's environment comes from CLIO's own uv, in the workspace:
  `"$CLIO_UV" venv .venv --python 3.12`, then `"$CLIO_UV" pip install --python .venv
  torch torchvision --index-url https://download.pytorch.org/whl/cpu` and
  `"$CLIO_UV" pip install --python .venv qiskit qiskit-machine-learning`. Datasets in
  the workspace's cache folder are not downloaded again on a rerun.

## Training in the background, live

A dashboard that exists before the first epoch ends lets the person watch both models
learn while training runs:

- `open_stream("qml-training")` returns the stream's `view_uri`.
- `references/training-dashboard.json` takes the `view_uri` in its two charts and the
  task in its scope line, and `create_a2ui_surface` publishes it. Its two
  `trajectories` charts follow the stream: loss and training accuracy over `epoch`, one
  line per `model`.

`run_code`'s kernel is CLIO's own Python: it has the stream and task bindings, but not
the packages installed for the model. So the training script runs in the
`.venv` that has them, prints one JSON line per model per epoch, and a background
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

The notification wakes the conversation; polling the task adds nothing.

## Evaluation on three backends, one job each

- The test inputs' features come from the trained classical part in `run_code`, one
  parameter set per input: the features in the order of the circuit's input
  parameters, then the trained weights in the order of its weight parameters.
  `circuit.parameters` (sorted by name) gives that order.
- The server reads the circuit as OpenQASM 3 in standard gates (transpiled to
  `["h", "p", "cx", "ry", "rz"]` before `qasm3.dumps`).
- `run_estimator` runs once on `local_exact` and once on a `fake_<device>`, each with
  all the parameter sets in `parameter_values` and the model's observable (for a
  two-qubit model, `"ZZ"`). A third call on a real device needs a key and the person's
  go-ahead, within the `ibm-quantum-budget` limits.
- `view_circuit` with the feature map and the ansatz as `blocks`; `view_layout` for
  the noisy job; `view_results` with the jobs and the true labels as `expected`.
- `compare_jobs` with `expected` gives accuracy per job and the inputs whose class
  flipped under noise, at the threshold the model's output uses (an expectation
  value at or above 0 is class 1 unless the model maps it otherwise).

## What the comparison shows

- Accuracy per backend for the hybrid model and the baseline, each tied to its job id.
- A two-class task on a reduced dataset is easy for both models, so equal accuracy is
  expected and is not evidence of a quantum advantage. What the comparison shows is how
  much the device's noise moves the expectation values and which inputs sit near the
  decision boundary.
- Why one input flipped is in the selected parameter set in the results view (its
  exact and noisy values and how close it is to the threshold) and in the layout (the
  two-qubit gates and swaps the device added), not in general text.

## As a study

The comparison is a small study; in the science log (`run-a-study`) it can be read,
compared and extended later:

- A `question` entry: how the device's noise changes this classifier's predictions.
- An `experiment` entry: the trained model, the test inputs and the backends.
- One `observation` per evaluation job, citing its `run_estimator` call in
  `from_calls`, with the job's accuracy, the mean shift from the exact values and the
  number of flipped inputs as `measurements` (`conditions`: the backend).
- An `evidence` entry for what the comparison supports, with its honest `strength`.
