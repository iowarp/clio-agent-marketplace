---
name: structure-from-name
description: Use when the person names a molecule or gives a SMILES and wants it built, shown or used in a calculation - from the name to a checked 3D structure file, asking when the name is ambiguous.
keywords: [alembic, structure, name, smiles, pubchem]
---

# From a name to a checked 3D structure

1. **Resolve the name** with `pubchem-lookup`. Ambiguous (isomers, a racemate, salt or
   free base): show the candidates and ask; do not pick. A SMILES given by the person
   needs no lookup; still check it parses.
2. **Get 3D coordinates:** PubChem's 3D conformer (`fetch_structure`) when it has one,
   else `smiles_to_structure` from the SMILES. Say which, and that either is a starting
   geometry.
3. **Check it:** `inspect_structure` for the formula (with hydrogens), charge and any
   undefined stereocentre; fix or ask before computing.
4. **Show it** in Burette (`open_structure`) from the workspace file when the connector is
   on, and answer questions about it from the person's selection: atom indices,
   elements and neighbours from the view state, distances and angles computed with
   `inspect_structure`, never read off the picture.

Hand the file path, not coordinates, to every next step.
