---
name: burette-views
title: Seeing and editing structures in Burette
description: Use when a molecule, crystal, protein, trajectory or vibration should be shown to the person, when they point at part of a structure ("this ring", "the atoms I selected", "what am I looking at"), when a bond length, angle or dihedral is to be changed by hand, or when they want to draw or edit a molecule in 2D.
keywords: [burette, molstar, ketcher, viewer, selection, trajectory, normal mode, level:L2]
---

# Seeing and editing structures in Burette

The Burette connector opens a viewer (Mol*) or a 2D editor (Ketcher) in the conversation.
Files are opened by path; nothing is uploaded.

## Which tool

| Need | Tool |
| --- | --- |
| Show a structure file (PDB, mmCIF, CIF with its cell, SDF/MOL, XYZ, GRO, MOL2) | `open_structure` (`frame`, `focus`, `supercell` for a crystal) |
| Play a vibration or a short trajectory (a multi-frame XYZ) | `play_mode` |
| A protein by its PDB ID | `open_pdb_entry` |
| What a file contains (chains, ligands, waters, elements) | `summarize_structure` |
| Set a bond length, angle or dihedral | `set_geometry` (writes `<name>.editN.<ext>` beside the source and opens it) |
| Move one atom | `move_atom` |
| Extract, remove or replace a fragment of a PDB | `edit_fragment` |
| Draw or edit a molecule in 2D | `open_ketcher` (seeded with SMILES, a MOL block or a file), then `get_ketcher_structure` and `save_ketcher_structure` |

## What the person is looking at

The viewer reports to you what the person selected, the region they framed, the frame of
a trajectory, the playing mode and the focus. When they say "this", read it from the
view's state (`get_view_state`; `describe_region` for a framed region) rather than
guessing, and name the atoms by element and index. You can move the view yourself:
`set_frame`, `play_mode`, `focus`.

## In a dashboard, linked to charts

The viewer can sit in a dashboard beside charts (the `create-dashboard` skill): a
`clio.mcp-app.v1` component with server `burette`, tool `open_structure` (or `play_mode`)
and the file the view already shows, so the dashboard shows the live view rather than a
picture. The view reports `frame` (0-based) and takes it back through `set_frame`, so the
state channel `{key: "frame", path: "/selection/frame", tool: "set_frame"}` links it to a
chart that selects on the same path, both ways. Likewise `mode` with `play_mode` (a mode's
animation path) and `focus`.

- An optimization: the trajectory (`opt_trajectory.xyz`) in the view and a line chart of
  `opt_steps.csv` (energy and largest force against step, one row per frame) selecting
  `step` on `/selection/frame`: picking a step moves the viewer to that frame, and playing
  the view moves the chart's marker.
- Frequencies: a table or IR stick chart of `frequencies.csv` selecting the mode's
  animation path on `/selection/mode`, so picking a mode plays it.
- Species or materials (a reaction diagram, a screening table): a column with each
  structure's path, selecting on `/selection/path`, opens that structure.

What the person picks on the chart reaches you as the view's state and the chart's
selection; answer from those rows and from the structure file, not from the picture.

## Edits make new files

Every geometry edit writes a new file and leaves the source unchanged; the result names
the file and the value measured from it. Ring bonds cannot be set this way (the ring
would break): say so and suggest a constrained optimization instead. A hand-edited
geometry is a starting point: optimize it before computing properties.

Burette is for looking and quick internal-coordinate edits. Building a structure from
fragments, changing elements or making surfaces and supercells is Avogadro's
(`avogadro-building`, when the Avogadro connector is enabled).
