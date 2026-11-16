---
name: find-compounds
title: Find compounds in PubChem
description: Use when the person names a compound (a common, trade or IUPAC name) and the work needs its identity, formula, SMILES or a 3D structure, or when a name may mean several compounds (isomers, a racemate or one enantiomer, a salt or the free base).
keywords: [pubchem, compound, name, smiles, cid, isomer, level:L2]
---

# Find compounds in PubChem

`resolve_name` turns a name into one PubChem compound, or into candidates when the name
is ambiguous or unknown. It never picks the first match for you, and neither do you.

## Resolved

The result gives the CID, title, IUPAC name, formula, molecular weight, SMILES, InChIKey
and stereocentre counts. If the record has undefined stereocentres and the question
depends on a specific stereoisomer, ask which one. Say which CID you used.

## Ambiguous

Show the person the candidates that fit the question (name, formula, what distinguishes
them) and ask with `ask_user` which they mean, unless the question itself settles it (say
how). Do not continue with a guess.

## Structures

`fetch_structure(cid)` writes PubChem's 3D conformer as SDF with hydrogens. When PubChem
has none (metals, salts, large flexible molecules), the result says so and writes the flat
2D record: build 3D coordinates from the SMILES with the ASE connector's
`smiles_to_structure` instead, and say that the geometry is generated, not PubChem's.
A PubChem conformer is a starting geometry; optimize before computing properties.

`get_compound` gives a CID's record and synonyms (CAS numbers, common names).
Network access to PubChem is needed; `pubchem_unavailable` means it could not be reached
after retries: say so and try later.
