---
name: ibm-quantum-budget
title: Real hardware within the time left
description: Use before any run on a real IBM quantum computer, and when the person asks about their IBM Quantum account, key, instance, plan, queue or time left. Triggers on "run it on real hardware", "IBM quantum computer", "how much time do I have", "set up my key", "least busy device".
keywords: [quantum, ibm-quantum, hardware, budget, open-plan, level:L2]
---

# Real hardware within the time left

Simulation needs nothing. A real device needs the person's IBM Quantum API key and
their instance's CRN, set in the IBM Quantum connector, and it spends quantum time
the person has a limited amount of.

## What the time is

- The free Open Plan gives a small allowance of quantum execution time per rolling
  period. Only execution time on the device counts, not the queue and not the
  transpile.
- `usage_info` says the limit, the seconds consumed and the seconds left. Read it
  before any hardware run and say the number to the person.
- Every hardware run reads the time left first and refuses a job whose estimate
  exceeds it, with both numbers; nothing is submitted then. Every hardware result
  says the seconds it used and the seconds left.

## Keep runs small

- Shots around 1000 for a Sampler run. Do not raise them without a reason you can
  state.
- One job per batch of inputs: a list of parameter sets in one call.
- Simulate first on `local_exact`, then on a `fake_<device>`, and run on hardware
  only the circuit you have already checked.
- Zero-noise extrapolation multiplies the shots; leave it off unless the person asks.
- `least_busy_backend` picks a device; a queue can take minutes to hours. Watch a
  long one from a background task and tell the person when it finishes, rather
  than polling in the conversation.

## The key and the instance

- A hardware call without a key answers `key_needed` with the values it needs
  (`token`, `instance`). Ask with `offer_plugin` for the IBM Quantum connector,
  with a one-sentence reason and those needs, so the person can enter them in the
  card. If the card does not show the values, tell the person to open the IBM
  Quantum connector in Extensions and enter the API key and the instance CRN there.
  Never ask for the key in the conversation, and never write it anywhere.
- If the person says Not now, go on with local backends and say so.
- Never create an instance, pick a plan, or use an instance other than the one in
  the connector.
