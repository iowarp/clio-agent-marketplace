---
name: adsorption
description: Use when a question is about how much gas a porous solid (a MOF, zeolite, porous carbon) takes up, which framework is best for a separation or storage, or how uptake changes with pressure and temperature, before setting up grand-canonical Monte Carlo simulations.
keywords: [adsorption, gcmc, mof, zeolite, working capacity, isotherm, level:L1]
---

# Gas adsorption in porous solids

Grand-canonical Monte Carlo (GCMC) holds the framework rigid and lets gas molecules be
inserted, deleted and moved at a fixed temperature and gas pressure (chemical potential).
The average number of molecules adsorbed is the uptake, usually in mol/kg of framework.

## What decides the result

- **Force field:** Lennard-Jones parameters for framework atoms (generic, UFF-like) and a
  rigid model of the gas (TraPPE-style for CO2 and N2). Generic parameters rank frameworks
  better than they predict absolute uptakes.
- **Framework charges:** polar gases (CO2, H2O) interact with framework charges. Without
  charges these interactions are missing; with them, the result depends on how the charges
  were assigned. Say which.
- **The cell:** replicated so every width is at least twice the interaction cutoff.
- **Sampling:** enough initialization cycles to reach equilibrium and enough production
  cycles for a small error bar. Report the block-average error bar; a run whose error bar
  is a large fraction of the uptake needs more cycles.
- **Water:** strongly framework-dependent and slow to converge; treat single runs as
  indicative.

## Questions and quantities

- **Uptake at one condition:** one run per framework.
- **Isotherm:** a series of pressures at one temperature.
- **Working capacity** for swing processes: uptake at the adsorption condition minus at
  the desorption condition. Both runs must succeed for every framework compared; a
  framework missing one is excluded, not ranked on partial data.
- **Selectivity** needs mixtures, which single-component runs do not give.

## Report

Uptake (mol/kg) with its error bar, the conditions (K, Pa), the adsorbate, the force
field and charges used, the cycles, and the caveats above. For a ranking, the metric and
which frameworks were excluded and why.
