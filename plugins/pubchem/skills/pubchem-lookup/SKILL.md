---
name: pubchem-lookup
title: Find compounds in PubChem
description: Use when the person names a compound (a common, trade or IUPAC name) and the work needs its identity, formula, SMILES or a 3D structure, or when a name may mean several compounds (isomers, a racemate or one enantiomer, a salt or the free base).
keywords: [pubchem, compound, name, smiles, cid, isomer, level:L2]
---

# Find compounds in PubChem

`resolve_name` turns a name into one PubChem compound, or into candidates when the name
is ambiguous or unknown. It never picks the first match, and a guess among candidates is
not an identification.

## Resolved

The result gives the CID, title, IUPAC name, formula, molecular weight, SMILES, InChIKey
and stereocentre counts. A record with undefined stereocentres does not identify a specific
stereoisomer; when the question depends on one, which one is the person's to say. The CID
used identifies the compound for anyone reading the work.

## Ambiguous

Which candidate the person means is theirs to say (`ask_user`; name, formula, what
distinguishes them), unless the question itself settles it, and then how it settles it is
part of the answer.

## Structures

`fetch_structure(cid)` writes PubChem's 3D conformer as SDF with hydrogens. When PubChem
has none (metals, salts, large flexible molecules), the result says so and writes the flat
2D record; the ASE connector's `smiles_to_structure` builds 3D coordinates from the SMILES,
and that geometry is generated, not PubChem's. A PubChem conformer is a starting geometry,
not an optimized one.

`get_compound` gives a CID's record and synonyms (CAS numbers, common names).
Network access to PubChem is needed; `pubchem_unavailable` means it could not be reached
after retries.
