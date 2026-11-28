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
  carbenes and some metal complexes; radicals are doublets. An open-shell species' result
  holds for the multiplicity it was computed with.

H, S and G (and the zero-point energy) hold at one temperature and pressure.

## Reactions

ΔG = Σ ν G(products) − Σ ν G(reactants), with the stoichiometric coefficients ν, and the
same for ΔH and ΔE.

- The species combine only at **one level of theory, one temperature and one pressure**.
- A sum computed in code from the per-species results, with its per-species table, is
  checkable; mental arithmetic is not.
- A reaction that does not balance (atoms and charge) gives a meaningless difference.
- Changing only the temperature reuses the optimized structures and frequencies: only the
  thermochemistry changes, not the optimizations.


## Conformers and rotational barriers

Conformers come from building each one, or from one structure with the dihedral set to
other values; each is a conformer once optimized to a minimum with no imaginary modes.

A rotational barrier's saddle point comes from holding the dihedral at the eclipsed (or
chosen) value with a constraint and optimizing everything else; frequencies on that
structure then show one imaginary mode along the rotation if it is the saddle point.
Displacing along that mode both ways and re-optimizing without constraints should reach
minima on both sides. A relaxed scan (the dihedral held at a series of values, each
optimized) shows the whole profile as energy against angle.

Barrier = E(saddle point) − E(minimum), both at the same level. Electronic
energies and, when frequencies are available, zero-point-corrected or free-energy
barriers are different numbers.

## Binding energies

Basis-set superposition error inflates binding energies unless corrected.

An energy difference depends on whether it is electronic, ZPE-corrected or free energy,
and on what was left out (other conformers, solvent, a higher level). An experimental or
literature value, with its source, is the external check.
