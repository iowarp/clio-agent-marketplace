---
name: morphorm
title: Formulate and Run a Morphorm-Based Topology Optimization Study
description: Apply Morphorm's optimization workflow and solver interface as an alternative topology-optimization route to Tosca, without conflating the two toolchains' conventions, and run it as a batch job with bundled checks.
---

State which solver backend Morphorm is driving for this study and confirm
its input format and unit conventions explicitly — Morphorm's own
configuration schema, mesh format, and constraint declarations are not
interchangeable with a Tosca `.par` file even when the optimization problem
(objective, constraints, design/frozen regions) is conceptually the same.

Declare the objective, constraints, design/frozen regions, and any
manufacturing restrictions (overhang, extrusion, minimum feature size) in
Morphorm's own configuration format, and confirm the referenced analysis
model (mesh, materials, loads) is valid on its own before attributing an
optimization failure to the optimizer.

## Toolchain
Confirm every keyword against the supplied manual, never from memory.

1. **Mesh.** Write a Cubit journal and export an Exodus mesh. Give every block, node set and side set the exact
   name the specification uses; an unnamed block exports with an empty name. Check the mesh with
   `exo_summary.py` before going further (see "Bundled checks").
2. **Deck.** Write the Morphorm input deck. Find each keyword by searching a text copy of the manual: block,
   material, load, boundary condition, criterion, filter, optimizer, output and restart sections. Put comments on
   their own lines, never after a keyword on the same line.
3. **Translate.** Run XMLGenerator on the deck in a clean run directory. List the generated settings with
   `xml_params.py` and confirm that each declared setting appears with the intended value.
   - A setting that is in the deck but absent from the generated XML is not applied.
   - The manual often offers two equivalent forms: a `begin filter … end filter` block, or study-level keywords
     such as `filter_type` and `filter_radius_absolute`. If a setting from one form, for example a filter's
     symmetry-plane side sets, does not reach the generated XML, re-translate once with the manual's equivalent
     form and compare again before you submit anything.
4. **Run.** Submit the generated run script as a Slurm batch job (load `hpc-batch-jobs`). Follow the optimizer
   diagnostics file while it runs.
5. **Deliver.** Copy the mesh, deck, generated configuration, diagnostics and final iteration output to the
   required paths, with hashes if the packet asks for them.

## Restarts and continuations
When a run continues from a saved state of an earlier run:
- Read the manual's restart keywords and the earlier run's output, and decide which saved state is meant. Count
  the states stored in the restart file and note whether the restart index is 0- or 1-based. A file that stores
  iterations 0…N holds N+1 states.
- After submitting, compare the first objective of the new run with the earlier run's objective at the intended
  iteration: `diag_summary.py NEW_DIAGNOSTICS --compare-first-to VALUE`. A clear mismatch means the wrong state
  was read. Cancel at once, record why, fix the index and resubmit. Do not wait for the run to finish.

## Bundled checks
Use these instead of writing new verification programs. They are generic and print compact JSON or TSV.
`SKILL_ROOT` is the skill directory reported by `load_skill`. Source the packet's approved software loader first
if `netCDF4` is missing.

    python3 SKILL_ROOT/scripts/exo_summary.py mesh.exo --expect num_elem=N block:NAME:type=HEX8 nodeset:NAME=K sideset:NAME=K bbox_max=X,Y,Z
    python3 SKILL_ROOT/scripts/exo_summary.py final_output.exo        # time steps, nodal fields, min/max at last step
    python3 SKILL_ROOT/scripts/xml_params.py RUN_DIR "symmetry" "length scale" "iteration"   # generated settings; MISSING -> exit 1
    python3 SKILL_ROOT/scripts/diag_summary.py morphorm_oc_optimizer_diagnostics.txt          # rows, first/last iteration, stop message

Save their output under `work/` when the packet asks for verification records, for example
`... > work/verify/mesh.json`, instead of writing a separate script.

Track the optimization's convergence history separately from the
manufacturability and structural re-verification of the converged result,
the same separation `topology_optimization` requires regardless of which
solver produced the topology.

Return the Morphorm configuration and referenced analysis model, the declared
regions/restrictions, the optimization's convergence status, and traceability
back to the approved formulation. Without executed solver evidence, label it
`GENERATED_NOT_EXECUTED`.
