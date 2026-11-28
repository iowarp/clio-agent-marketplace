---
name: graspa-adsorption
title: Adsorption with gRASPA
description: Use when gas uptake (CO2, H2O, N2) in a MOF or zeolite CIF is to be simulated with the gRASPA connector, an isotherm or working capacity computed, or frameworks ranked.
keywords: [graspa, gcmc, adsorption, mof, zeolite, ranking, level:L2]
---

# Adsorption with the gRASPA connector

`adsorption` covers the method and its caveats. This is how the connector does it.

## One condition, one folder

`run_graspa` (gRASPA here) or `prepare_graspa` (a folder for a GPU node) takes a framework
CIF, one adsorbate (CO2, H2O or N2), temperature (K), pressure (Pa), initialization and
production cycles, `framework_charges` (`none`, or `cif` when the CIF has
`_atom_site_charge`) and the cutoff. The result notes when the framework is uncharged.
`read_graspa` reads a finished folder: uptake in mol/kg with its block-average error bar,
molecules per unit cell, mg/g, g/L and the Henry coefficient when printed.

`graspa_status` says whether gRASPA runs here; `install-graspa` covers getting it.

## Several frameworks or conditions

One folder per framework and condition. For an isotherm, a series of pressures; for a
working capacity, the adsorption and the desorption condition for every framework.
`rank_frameworks` ranks the result folders by uptake at one condition, or by working
capacity. Frameworks without every requested completed run are excluded with the reason;
their missing values are unknown, not fillable.

A few cycles show whether the setup runs; a ranking needs enough cycles for an error bar
small next to the differences ranked on. Uptakes or capacities mean something with their
error bars.
