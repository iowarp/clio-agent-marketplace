---
name: read-structure-images
title: Read structures from images
description: Use when a chemical structure exists only as a picture - a figure in a paper, a screenshot, a photo of a whiteboard or notebook - and it is needed as SMILES or a structure file.
keywords: [decimer, ocsr, image, smiles, structure recognition, level:L2]
---

# Read a structure from an image

`image_to_smiles` reads one drawn structure with the DECIMER model and checks the SMILES
with RDKit. Its result is **the model's reading**, not a fact.

1. If the image holds several structures or text, crop to one first (`crop_image`, in
   pixels or fractions). Look at the image yourself (`view_image`) to choose the box.
2. Run `image_to_smiles`. Read its confidence and any RDKit problem.
3. Show the person the reading before using it: the SMILES, formula and, when the Burette
   connector is enabled, open it in Ketcher (`open_ketcher` seeded with the SMILES) so they
   can compare it with the picture and correct it. Use the corrected structure
   (`get_ketcher_structure`) if they change it.
4. Low confidence, an invalid SMILES, stereochemistry the drawing does not show clearly,
   abbreviations (Ph, Boc, R groups) or a Markush structure: say what is uncertain and ask.

The first call downloads the model (about 285 MiB, a couple of minutes); say so before it
starts.
