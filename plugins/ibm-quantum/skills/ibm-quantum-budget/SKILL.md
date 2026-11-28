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
- `usage_info` says the limit, the seconds consumed and the seconds left. The person
  knows the seconds left before a hardware run spends any of them.
- Every hardware run reads the time left first and refuses a job whose estimate
  exceeds it, with both numbers; nothing is submitted then. Every hardware result
  says the seconds it used and the seconds left.

## What a run costs

- Shots around 1000 suffice for a Sampler run; more shots spend more of the time.
- A batch of inputs is one job: a list of parameter sets in one call.
- `local_exact` and a `fake_<device>` spend no quantum time, so a circuit checked on
  them is what hardware time is worth spending on.
- Zero-noise extrapolation multiplies the shots, so it runs only when the person asks
  for it.
- `least_busy_backend` picks a device; a queue can take minutes to hours. A background
  task can watch a long one and notify when it finishes; polling in the conversation
  only spends turns.

## The key and the instance

- A hardware call without a key answers `key_needed` with the values it needs
  (`token`, `instance`). `offer_plugin` for the IBM Quantum connector, with a
  one-sentence reason and those needs, shows a card where the person enters them; the
  IBM Quantum connector in Extensions also takes the API key and the instance CRN. The
  key never passes through the conversation and is never written anywhere.
- After Not now, the local backends still work.
- The instance and plan are the person's: runs use only the instance in the connector,
  and creating an instance or choosing a plan is theirs to do.
