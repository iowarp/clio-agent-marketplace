---
name: structure-from-image
title: Read structures from images
description: Use when a chemical structure exists only as a picture - a figure in a paper, a screenshot, a photo of a whiteboard or notebook - and it is needed as SMILES or a structure file.
keywords: [decimer, ocsr, image, smiles, structure recognition, level:L2]
---

# Read a structure from an image

`image_to_smiles` reads one drawn structure with the DECIMER model and checks the SMILES
with RDKit. Its result is **the model's reading**, not a fact.

- The model reads one structure at a time. An image with several structures or text reads
  after cropping to one (`crop_image`, in pixels or fractions); `view_image` shows the
  image to choose the box.
- `image_to_smiles` returns a confidence and any RDKit problem alongside the SMILES.
- The person can compare the reading with the picture: the SMILES and formula, and, when
  the Burette connector is enabled, Ketcher (`open_ketcher` seeded with the SMILES), where
  they can correct it; `get_ketcher_structure` returns their corrected structure.
- Low confidence, an invalid SMILES, stereochemistry the drawing does not show clearly,
  abbreviations (Ph, Boc, R groups) and Markush structures are where readings go wrong.

The first call downloads the model (about 285 MiB, a couple of minutes).
