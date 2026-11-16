---
name: geometry-and-frequencies
description: Use after any structure optimization, frequency, thermochemistry or energy calculation, before reporting it, to check that it means what it claims - converged, a minimum or a saddle point as intended, the right charge and spin, the units stated - and to say what was not checked.
keywords: [chemistry, convergence, imaginary frequency, transition state, units, level:L1]
---

# Check a calculation before you report it

A finished calculation is not a result yet. Read its output and check each point below;
report what you checked and what you could not.

## Did it converge?

- **Optimization:** converged flag, the final largest force against the threshold, and
  the number of steps against the limit. Not converged: say so, restart from the last
  frame, never report its geometry as optimized.
- **SCF or electronic structure:** the program's own convergence message. An unconverged
  SCF makes every later number suspect.

## Is it the stationary point you wanted?

Count the imaginary frequencies (reported as negative or with an `i`).

| Imaginary modes | Meaning | Next step |
| --- | --- | --- |
| 0 | a minimum | report it |
| 1, wanted a minimum | a saddle point | look at the mode (play it); displace along it both ways, re-optimize, and compare |
| 1, wanted a transition state | a candidate transition state | check the mode connects the intended minima |
| more than 1 | a higher-order saddle point or a poor optimization | re-optimize tighter, or displace along each mode |

Very small imaginary modes (under about 50 cm⁻¹) often come from a loose optimization or
numerical noise; tighten and recompute before interpreting them. Thermochemistry from a
structure with imaginary modes leaves them out; say so.

## Charge, spin, composition

- The charge and multiplicity used match the species (count electrons: an odd count needs
  an even multiplicity).
- The method models charge and spin; if not, the number ignores them.
- The formula and atom count of the final structure match the input (nothing dissociated,
  no atom lost or added).

## Units and conditions

State units with every number: eV or kJ/mol (1 eV = 96.485 kJ/mol), cm⁻¹, Å, degrees, K,
Pa. Thermochemistry depends on temperature and pressure; state both. Free energies need
the standard state stated.

## What to say

One line per check: what was checked and its outcome, and a list of what was not checked
(a conformer search, a basis-set check, a larger method). Never present a single
calculation as the answer to a question it cannot settle.
