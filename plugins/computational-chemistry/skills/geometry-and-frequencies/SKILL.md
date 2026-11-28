---
name: geometry-and-frequencies
description: Use after any structure optimization, frequency, thermochemistry or energy calculation, before reporting it, to check that it means what it claims - converged, a minimum or a saddle point as intended, the right charge and spin, the units stated - and to say what was not checked.
keywords: [chemistry, convergence, imaginary frequency, transition state, units, level:L1]
---

# What a calculation's output shows

A finished calculation is not a result yet: its output shows whether it means what it
claims, and some points cannot be checked from one calculation.

## Did it converge?

- **Optimization:** converged flag, the final largest force against the threshold, and
  the number of steps against the limit. An unconverged optimization's geometry is not
  optimized; its last frame is a starting point for a restart.
- **SCF or electronic structure:** the program's own convergence message. An unconverged
  SCF makes every later number suspect.

## Is it the stationary point you wanted?

Count the imaginary frequencies (reported as negative or with an `i`).

| Imaginary modes | Meaning | What resolves it |
| --- | --- | --- |
| 0 | a minimum | |
| 1, wanted a minimum | a saddle point | the mode (played) shows the motion; displacing along it both ways and re-optimizing finds the minima |
| 1, wanted a transition state | a candidate transition state | whether the mode connects the intended minima |
| more than 1 | a higher-order saddle point or a poor optimization | a tighter re-optimization, or displacement along each mode |

Very small imaginary modes (under about 50 cm⁻¹) often come from a loose optimization or
numerical noise, and tighter settings remove them. Thermochemistry from a structure with
imaginary modes leaves them out.

## Charge, spin, composition

- The charge and multiplicity used match the species (count electrons: an odd count needs
  an even multiplicity).
- The method models charge and spin; if not, the number ignores them.
- The formula and atom count of the final structure match the input (nothing dissociated,
  no atom lost or added).

## Units and conditions

A number means something with its unit: eV or kJ/mol (1 eV = 96.485 kJ/mol), cm⁻¹, Å, degrees, K,
Pa. Thermochemistry depends on temperature and pressure, and free energies on the
standard state.

## What one calculation cannot settle

A single calculation does not check its conformer, its basis set or a larger method;
those are separate calculations.
