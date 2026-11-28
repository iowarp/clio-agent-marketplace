---
name: morphorm
title: Set Up, Run and Check a Morphorm Topology Optimization
description: Use to run a Morphorm study end to end (Cubit mesh, input deck, XMLGenerator, batch run, restart, delivery) and verify each step with the bundled checks.
keywords:
- level:L2
- morphorm
- topology-optimization
---

Morphorm is one topology-optimization program a study can use. The method
(stating the problem, checking the analysis model, reading the result as a
proposal) is in `topology-optimization`. Morphorm
has its own deck, mesh format and keywords: none of them carry over from
another optimizer's input, even when the optimization problem is the same.

The analysis the study drives, its units, and the objective, constraints,
design and frozen regions and manufacturing restrictions constrain the run
only as declared in Morphorm's own input. A failure belongs to the optimizer
only when the analysis model (mesh, materials, loads, supports) is valid on
its own.

## Toolchain

Keywords come from the installed or supplied Morphorm manual; memory gets them
wrong. A text copy of the manual is searchable.

Each stage feeds the next:

- **Mesh.** A Cubit journal exports an Exodus mesh. Blocks, node sets and side
  sets carry the exact names the specification uses; an unnamed block exports
  with an empty name. `exo_summary.py` shows the mesh (see "Bundled checks").
- **Deck.** The Morphorm input deck's keywords are in the manual: block,
  material, load, boundary condition, criterion, filter, optimizer, output and
  restart sections. Comments go on their own lines; one after a keyword on the
  same line breaks it.
- **Translate.** XMLGenerator runs on the deck in a clean run directory.
  `xml_params.py` lists the generated settings, showing whether each declared
  setting appears with the intended value.
   - A setting that is in the deck but absent from the generated XML is not
     applied.
   - The manual often offers two equivalent forms: a `begin filter … end
     filter` block, or study-level keywords such as `filter_type` and
     `filter_radius_absolute`. If a setting from one form, for example a
     filter's symmetry-plane side sets, does not reach the generated XML, the
     manual's equivalent form often does.
- **Run.** The generated run script runs as a batch job (`hpc-batch-jobs` on
  Slurm). The optimizer diagnostics file shows progress while it runs.
- **Deliverables.** The mesh, deck, generated configuration, diagnostics and
  final iteration output, with hashes when the task asks for them.

## Restarts and continuations

When a run continues from a saved state of an earlier run:

- The manual's restart keywords and the earlier run's output say which saved
  state is meant. The restart file stores a number of states, and the restart
  index is 0- or 1-based. A file that stores
  iterations 0…N holds N+1 states.
- The first objective of the new run matches the earlier run's objective at the
  intended iteration when the right state was read:
  `diag_summary.py NEW_DIAGNOSTICS --compare-first-to VALUE`. A clear mismatch
  means the wrong state was read, and every further iteration of that run is
  wasted compute.

## Bundled checks

These cover the verification; they are generic and print compact JSON or TSV.
`SKILL_ROOT` is the skill directory reported by `load_skill`. `exo_summary.py`
needs numpy and netCDF4; where `import netCDF4` fails, the site's approved
software environment provides them.

    python3 SKILL_ROOT/scripts/exo_summary.py mesh.exo --expect num_elem=N block:NAME:type=HEX8 nodeset:NAME=K sideset:NAME=K bbox_max=X,Y,Z
    python3 SKILL_ROOT/scripts/exo_summary.py final_output.exo        # time steps, nodal fields, min/max at last step
    python3 SKILL_ROOT/scripts/xml_params.py RUN_DIR "symmetry" "length scale" "iteration"   # generated settings; MISSING -> exit 1
    python3 SKILL_ROOT/scripts/diag_summary.py DIAGNOSTICS.txt        # rows, first/last iteration, stop message

Their output, saved under the work directory (for example
`... > work/verify/mesh.json`), is a verification record.

A package without executed solver evidence is `GENERATED_NOT_EXECUTED`.
