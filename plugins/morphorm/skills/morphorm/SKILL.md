---
name: morphorm
title: Set Up, Run and Check a Morphorm Topology Optimization
description: Run a Morphorm study end to end (Cubit mesh, input deck, XMLGenerator, batch run, delivery), confirm every declared setting reached the generated XML, pick and check the saved state for a restart, and verify each step with the bundled checks instead of new one-off programs.
keywords:
- level:L2
- morphorm
- topology-optimization
---

Morphorm is one topology-optimization program a study can use. The method
(stating the problem, checking the analysis model, reading the result as a
proposal) is in `topology-optimization`; load it alongside this skill. Morphorm
has its own deck, mesh format and keywords: none of them carry over from
another optimizer's input, even when the optimization problem is the same.

State which analysis the study drives, its units, and the objective,
constraints, design and frozen regions and manufacturing restrictions, all
declared in Morphorm's own input. Confirm the analysis model (mesh, materials,
loads, supports) is valid on its own before attributing a failure to the
optimizer.

## Toolchain

Confirm every keyword against the installed or supplied Morphorm manual,
never from memory. Convert the manual to text once and search it for the
sections you need.

1. **Mesh.** Write a Cubit journal and export an Exodus mesh. Give every
   block, node set and side set the exact name the specification uses; an
   unnamed block exports with an empty name. Check the mesh with
   `exo_summary.py` before going further (see "Bundled checks").
2. **Deck.** Write the Morphorm input deck. Find each keyword by searching the
   text copy of the manual: block, material, load, boundary condition,
   criterion, filter, optimizer, output and restart sections. Put comments on
   their own lines, never after a keyword on the same line.
3. **Translate.** Run XMLGenerator on the deck in a clean run directory. List
   the generated settings with `xml_params.py` and confirm that each declared
   setting appears with the intended value.
   - A setting that is in the deck but absent from the generated XML is not
     applied.
   - The manual often offers two equivalent forms: a `begin filter … end
     filter` block, or study-level keywords such as `filter_type` and
     `filter_radius_absolute`. If a setting from one form, for example a
     filter's symmetry-plane side sets, does not reach the generated XML,
     re-translate once with the manual's equivalent form and compare again
     before you submit anything.
4. **Run.** Submit the generated run script as a batch job (on Slurm, load
   `hpc-batch-jobs`). Follow the optimizer diagnostics file while it runs.
5. **Deliver.** Copy the mesh, deck, generated configuration, diagnostics and
   final iteration output to the required paths, with hashes if the task asks
   for them.

## Restarts and continuations

When a run continues from a saved state of an earlier run:

- Read the manual's restart keywords and the earlier run's output, and decide
  which saved state is meant. Count the states stored in the restart file and
  note whether the restart index is 0- or 1-based. A file that stores
  iterations 0…N holds N+1 states.
- After submitting, compare the first objective of the new run with the
  earlier run's objective at the intended iteration:
  `diag_summary.py NEW_DIAGNOSTICS --compare-first-to VALUE`. A clear mismatch
  means the wrong state was read. Cancel at once, record why, fix the index
  and resubmit. Do not wait for the run to finish.

## Bundled checks

Use these instead of writing new verification programs. They are generic and
print compact JSON or TSV. `SKILL_ROOT` is the skill directory reported by
`load_skill`. `exo_summary.py` needs numpy and netCDF4; if `import netCDF4`
fails, load the site's approved software environment first.

    python3 SKILL_ROOT/scripts/exo_summary.py mesh.exo --expect num_elem=N block:NAME:type=HEX8 nodeset:NAME=K sideset:NAME=K bbox_max=X,Y,Z
    python3 SKILL_ROOT/scripts/exo_summary.py final_output.exo        # time steps, nodal fields, min/max at last step
    python3 SKILL_ROOT/scripts/xml_params.py RUN_DIR "symmetry" "length scale" "iteration"   # generated settings; MISSING -> exit 1
    python3 SKILL_ROOT/scripts/diag_summary.py DIAGNOSTICS.txt        # rows, first/last iteration, stop message

When the task asks for verification records, save their output under the
work directory (for example `... > work/verify/mesh.json`) instead of writing
a separate script.

## Return

The Morphorm deck and the analysis model it references, the declared regions
and restrictions, the generated settings confirmed by `xml_params.py`, every
job id submitted, the optimization's convergence status and stop message, and
traceability to the approved formulation. Without executed solver evidence,
label the package `GENERATED_NOT_EXECUTED`.
