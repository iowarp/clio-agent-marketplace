---
name: thermochemistry
description: Use when the question is a thermodynamic quantity or an energy difference - enthalpy, entropy or Gibbs energy of a species, a reaction energy or Gibbs energy, a rotational or reaction barrier, the relative energy of conformers or isomers - to compute every species the same way and combine them in code with stoichiometry.
keywords: [chemistry, thermochemistry, gibbs energy, reaction energy, barrier, conformer, spin state, level:L1]
---

# Thermochemistry and energy differences

## One species

Ideal-gas thermochemistry needs a converged minimum with no imaginary modes
(`geometry-and-frequencies`), the vibrational frequencies, and three facts about the
molecule:

- **Geometry class:** linear or nonlinear (rotational and vibrational degrees of freedom
  differ).
- **Rotational symmetry number** from the point group (1 for C1, 2 for C2v such as
  water, 3 for C3v such as ammonia, 12 for Td such as methane, 2 for linear D∞h such as
  CO2 and O2). A wrong one shifts the entropy by R ln(ratio).
- **Spin state:** the electronic multiplicity enters the entropy as R ln(2S+1), and the
  energy depends on it. Know each species' ground state: O2 is a triplet, as are many
  carbenes and some metal complexes; radicals are doublets. Say which multiplicity was
  used for every open-shell species.

Report H, S and G (and the zero-point energy) at a stated temperature and pressure.

## Reactions

ΔG = Σ ν G(products) − Σ ν G(reactants), with the stoichiometric coefficients ν, and the
same for ΔH and ΔE. Rules:

- Every species at **one level of theory, one temperature and one pressure**.
- Compute the sum **in code** from the per-species results, never by mental arithmetic,
  and keep the per-species table with the answer.
- Check the reaction balances (atoms and charge) before computing it.
- Changing only the temperature reuses the optimized structures and frequencies: recompute
  the thermochemistry, not the optimizations.


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

## Binding energies

Say whether basis-set superposition error was corrected.

## Report

The difference with units (kJ/mol and eV), the level of theory, whether it is
electronic, ZPE-corrected or free energy, and what was left out (other conformers,
solvent, a higher level). Compare with an experimental or literature value when one is
known, and give its source.
