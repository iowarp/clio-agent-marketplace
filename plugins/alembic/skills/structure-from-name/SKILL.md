---
name: structure-from-name
description: Use when the person names a molecule or gives a SMILES and wants it built, shown or used in a calculation - from the name to a checked 3D structure file, asking when the name is ambiguous.
keywords: [alembic, structure, name, smiles, pubchem]
---

# From a name to a checked 3D structure

- **The name:** `pubchem-lookup` resolves it. An ambiguous name (isomers, a racemate, salt
  or free base) has several candidates, and which one is meant is the person's to say. A
  SMILES given by the person needs no lookup, though it may still fail to parse.
- **3D coordinates:** PubChem's 3D conformer (`fetch_structure`) when it has one, else
  `smiles_to_structure` from the SMILES. Either is a starting geometry.
- **Checks:** `inspect_structure` gives the formula (with hydrogens), charge and any
  undefined stereocentre; an error there carries into every calculation after it.
- **Burette** (`open_structure`) shows the workspace file when the connector is on. The
  person's selection there carries atom indices, elements and neighbours in the view
  state; distances and angles come from `inspect_structure`, not from the picture.

Each next step takes the file path; coordinates need no retyping.
