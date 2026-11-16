---
name: chemistry-study
title: A chemistry study from question to checked result
description: Use at the start of a computational chemistry request - a property, energy, barrier, spectrum or adsorption question about named or drawn compounds or a crystal - to plan the steps from identifying the system to a checked, reported result, and to record the study.
keywords: [chemistry, study, plan, workflow, alembic]
---

# From question to checked result

1. **Identify the system.** A name: `find-compounds` (ask when it is ambiguous). A
   picture: `read-structure-images` (the person confirms the reading). A file: inspect
   it. A crystal: the CIF the person gives, or ask where it comes from.
2. **Say what will answer the question.** The quantity, the method (`choose-a-method`),
   the program, and roughly how long. Ask before a long or expensive run, or an install.
3. **Build the starting structures** and show them in Burette when it is enabled, so the
   person sees what is being computed.
4. **Compute**, smallest useful step first (one structure, a short run) before a series.
5. **Check** every result with `check-a-calculation`; for differences use
   `reaction-and-conformer-energies`, for spectra `x-ray-absorption`, for uptake
   `gas-adsorption`.
6. **Report** the numbers with units, the method and settings, the checks and what was not
   done; link the result files; plot when a profile, spectrum or ranking is involved; show
   the key structure or mode.
7. **Record** the study in the study log: question, structures (paths and hashes),
   methods, results, checks, open points.

When a connector a step needs is off or a program is missing, say which, offer to enable
or install it, and continue with what is available.
