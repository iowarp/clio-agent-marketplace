---
name: reaction-and-conformer-energies
description: Use when the question is an energy difference - a rotational or reaction barrier, the relative energy of conformers or isomers, a reaction or binding energy - to set up the endpoints and the path, and to report the difference with its level of theory and what it leaves out.
keywords: [chemistry, barrier, conformer, reaction energy, scan, level:L1]
---

# Energy differences: barriers, conformers, reactions

Every energy difference is a difference between two well-defined structures computed the
same way. Set up both ends, check both (`check-a-calculation`), then subtract.

## Conformers and rotational barriers

1. Build each conformer, or one and generate others by setting the dihedral.
2. Optimize each to a minimum and confirm no imaginary modes.
3. For a rotational barrier: hold the dihedral at the eclipsed (or chosen) value with a
   constraint, optimize everything else, then compute frequencies on that structure. One
   imaginary mode along the rotation means it is the saddle point. Displace along that mode
   both ways and re-optimize without constraints: both should reach minima.
4. A relaxed scan (the dihedral held at a series of values, each optimized) shows the
   whole profile; plot energy against angle.

Barrier = E(saddle point) − E(minimum), both at the same level. Report electronic
energies and, when frequencies are available, zero-point-corrected or free-energy
barriers, saying which.

## Reaction and binding energies

ΔE = Σ E(products) − Σ E(reactants), every species optimized at the same level, with
the same charge bookkeeping. For binding energies, say whether basis-set superposition
error was corrected. Free energies need thermochemistry at a stated temperature and
pressure for each species.

## Report

The difference with units (kJ/mol and eV), the level of theory, whether it is
electronic, ZPE-corrected or free energy, and what was left out (other conformers,
solvent, a higher level). Compare with an experimental or literature value when one is
known, and give its source.
