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

## Linking charts to the viewer

The viewer's `frame`, `mode` and `focus` are state channels an A2UI chart can drive: an
optimization's energy-and-force chart linked by step moves the viewer to that frame; a
frequency table or IR spectrum linked by mode plays that mode; a species in a reaction
energy diagram or a row in a screening table can open its structure. Build such charts
from the result CSVs (one row per step, mode or species, with the structure path or frame
index as a column) so a selection carries enough to act on.

## Edits make new files

Every geometry edit writes a new file and leaves the source unchanged; the result names
the file and the value measured from it. Ring bonds cannot be set this way (the ring
would break): say so and suggest a constrained optimization instead. A hand-edited
geometry is a starting point: optimize it before computing properties.

Burette is for looking and quick internal-coordinate edits. Building a structure from
fragments, changing elements or making surfaces and supercells is Avogadro's
(`avogadro-building`, when the Avogadro connector is enabled).
