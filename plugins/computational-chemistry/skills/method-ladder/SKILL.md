---
name: method-ladder
description: Use before any energy, geometry, frequency or spectrum calculation on a molecule or crystal, to choose the level of theory (force field, semi-empirical tight binding, machine-learned potential, DFT or wavefunction) for the question, the system and the time available, and to say what the choice can and cannot show.
keywords: [chemistry, level of theory, dft, xtb, machine-learned potential, level:L1]
---

# Choose a method for the question

A calculation answers one question at one level of theory. The question, the elements and
the size of the system decide which level fits, and each level has things it can and
cannot show. Programs are separate (each has its own plugin); this skill is about the
method.

## The ladder

| Level | Good for | Not for | Cost |
| --- | --- | --- | --- |
| Classical force field (MMFF, UFF) | starting geometries, conformer search, very large systems | bond breaking, electronic structure, metals, spin | seconds |
| Semi-empirical tight binding (GFN2-xTB) | geometries, conformers, frequencies of organic and many inorganic molecules, quick barriers, dipoles and IR | quantitative reaction energies, unusual bonding, strongly correlated systems | seconds to minutes |
| Machine-learned potentials (MACE-OFF for organic molecules; MACE-MP for crystals; UMA across chemistry) | near-DFT geometries and energies inside the training domain, at force-field speed | elements, charges or spins outside the training data; a dipole (no IR) unless the model gives one | seconds to minutes; first use downloads the model |
| DFT (B3LYP, PBE0, ωB97X-D with a basis such as 6-31G* or def2-SVP/TZVP) | reaction and binding energies, barriers, spectra, open shells | dispersion without a correction; multireference cases | minutes to hours |
| Wavefunction (MP2, CCSD(T)) | benchmarks on small systems | anything large | hours |

Where each level fits:

- **Organic molecules, conformations, vibrations:** xTB or MACE-OFF are usually enough;
  DFT matters when the answer depends on a few kJ/mol.
- **Charged or open-shell systems:** xTB, DFT and UMA with its task model charge and
  spin. A potential that models neither gives a number that ignores them.
- **Metals and crystals:** periodic methods or potentials trained on crystals; EMT only
  for testing.
- **Spectra:** IR needs a dipole (xTB or DFT). X-ray absorption needs its own program
  (see `xanes`).
- **Adsorption in porous solids:** classical Monte Carlo with a force field (see
  `adsorption`), not electronic structure.

## Cost and choice

The cheapest level that can answer the question is often enough; a result close to a
decision is where the next level up changes things. When the level changes the answer (a
small energy difference, an open-shell state) and the calculation is long, the choice is
one the person may want to make (`ask_user`).

## Compare like with like

Energies are only comparable at the same level of theory, basis, charge, spin and
settings; a difference of energies from two methods is meaningless. A number is
reproducible with its method, model or functional, basis, charge, multiplicity and every
non-default setting.
