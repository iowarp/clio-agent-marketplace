---
name: choose-a-method
description: Use before any energy, geometry, frequency or spectrum calculation on a molecule or crystal, to choose the level of theory (force field, semi-empirical tight binding, machine-learned potential, DFT or wavefunction) for the question, the system and the time available, and to say what the choice can and cannot show.
keywords: [chemistry, level of theory, dft, xtb, machine-learned potential, level:L1]
---

# Choose a method for the question

A calculation answers one question at one level of theory. Choose the level from the
question, the elements and the size of the system, then say in the answer what that level
can and cannot show. Programs are separate (each has its own plugin); this skill is about
the method.

## The ladder

| Level | Good for | Not for | Cost |
| --- | --- | --- | --- |
| Classical force field (MMFF, UFF) | starting geometries, conformer search, very large systems | bond breaking, electronic structure, metals, spin | seconds |
| Semi-empirical tight binding (GFN2-xTB) | geometries, conformers, frequencies of organic and many inorganic molecules, quick barriers, dipoles and IR | quantitative reaction energies, unusual bonding, strongly correlated systems | seconds to minutes |
| Machine-learned potentials (MACE-OFF for organic molecules; MACE-MP for crystals; UMA across chemistry) | near-DFT geometries and energies inside the training domain, at force-field speed | elements, charges or spins outside the training data; a dipole (no IR) unless the model gives one | seconds to minutes; first use downloads the model |
| DFT (B3LYP, PBE0, ωB97X-D with a basis such as 6-31G* or def2-SVP/TZVP) | reaction and binding energies, barriers, spectra, open shells | dispersion without a correction; multireference cases | minutes to hours |
| Wavefunction (MP2, CCSD(T)) | benchmarks on small systems | anything large | hours |

Rules of thumb:

- **Organic molecules, conformations, vibrations:** xTB or MACE-OFF first. Move to DFT
  when the answer depends on a few kJ/mol.
- **Charged or open-shell systems:** use a method that models charge and spin (xTB,
  DFT, UMA with its task). A potential that models neither gives a number that ignores
  them; say so if it is used anyway.
- **Metals and crystals:** periodic methods or potentials trained on crystals; EMT only
  for testing.
- **Spectra:** IR needs a dipole (xTB or DFT). X-ray absorption needs its own program
  (see `x-ray-absorption`).
- **Adsorption in porous solids:** classical Monte Carlo with a force field (see
  `gas-adsorption`), not electronic structure.

## When the person did not say

Pick the cheapest level that can answer the question, say which and why in one line, and
offer the next level up if the result is close to a decision. When the choice changes the
answer (a small energy difference, an open-shell state), ask with `ask_user` before a long
calculation.

## Compare like with like

Energies are only comparable at the same level of theory, basis, charge, spin and
settings. Never subtract energies from two methods. Record the method, model or
functional, basis, charge, multiplicity and every non-default setting with each number.
