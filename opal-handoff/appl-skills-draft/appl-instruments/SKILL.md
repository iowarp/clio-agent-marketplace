---
name: appl-instruments
title: APPL instruments and what their traits mean
description: What each APPL-CORE sensor measures, how its traits are derived, and the caveats to check before interpreting them. Load when a question depends on what a trait physically means.
keywords:
- level:L2
- appl-core
- sensors
- instruments
---

# APPL instruments

> DRAFT (handoff). Content comes from the APPL-CORE export docs (`docs/modalities/*.md`,
> shipped in every export). **Read the export's own doc for any sensor you use**. This file is
> only an orientation. Items tagged **[inferred]** go beyond what the docs say and must be
> confirmed by the APPL team.

## The sensors the format can contain
Discover which ones are present from the manifest and README. Any given export has a subset.

| Id | What it is | Main traits | Check before trusting |
|---|---|---|---|
| RGB1 | Side-view colour camera | shape incl. height, colour, hue bins | [inferred] height is image-derived, not the manual height side table |
| RGB2 | Top-view colour camera | projected area, shape, colour, NGRDI, hue bins | **mm values use a hard-coded pixel scale** (docs: not calibrated): cross-check against 3D projected area; projected area **saturates** when canopies overlap or leave the crop (check bounding boxes against crop edges); a model (ViT) mask may be used instead of the vendor mask, and the two can differ a lot |
| FC1 | Chlorophyll fluorescence (FluorCam) | whole-plant vendor scalars + masked medians of parameter images, in **long** tables | the protocol varies by round (dark-adapted Fv/Fm vs light-response/quenching steps like `_L1.._Lss`, `_D1..`); pick one provenance kind; the `QY_max` (Fv/Fm) plausible range is roughly 0.75–0.85 for unstressed plants |
| FC2 | Multicolour fluorescence | protocol-dependent images (e.g. F440/F520/F690/F740) | [inferred] same long-table pattern as FC1 |
| IR1 | Thermal camera | median plant temperature (°C), shape | [inferred] temperature depends on ambient conditions; the export has no environment data |
| MSC1 | Multispectral 940/1450 nm | band stats + `r940/r1450` "water content" ratio | **a dimensionless ratio, not % water** (docs); check for rows blanked by an invalid-source flag |
| MSC2 | Root/rhizotron NIR | like MSC1, for roots | [inferred] |
| ROOT | Root imaging | RGB-like shape/colour on roots | docs: not a root-architecture pipeline |
| VNIR | Hyperspectral ~350–900 nm | 7 vegetation indices (PRI, NDVI, NDVI2, PSRI, SIPI, MCARI1, OSAVI) + per-band median signatures | **OSAVI and NDVI2 are implementation-specific formulas** (docs); reflectance is calibrated with white/dark references; check the red edge in signatures |
| SWIR | Hyperspectral ~900–1680 nm | `WATERCONTENT = R1440/R960` + signatures | a water-sensitive ratio, not absolute water; expect a dip near the 1450 nm water band |
| S3D | 3D scanner (point cloud + segmented surface) | surface/projected area, height, leaf inclination, LAI, compactness, digital biomass (height × area proxy), stem, branches; per-leaf long table | vendor units are `a.u.`, and the export maps them to mm/mm²; per-leaf segmentation can be coarse; geometry files are headerless whitespace text (points; vertices/faces/colours) |
| Weights (side table) | Scale before/after watering | `weight_g`, `weight_after_watering_g` | docs: may include pot/soil; **not plant mass**; check for scale errors (0 g, implausible spikes) |
| Heights (side table) | Manual/station height | `plant_height_mm` | only present in some exports |

## How images relate to plants
- **One thumbnail usually shows a tray** (several plants). Masks are per plant, in frame coordinates. Crop with the features table's ROI columns.
- **Grayscale thumbnails** (fluorescence, multispectral) are scaled values: `vmin + g/255·(vmax−vmin)` using the `thumbnail_vmin/vmax` columns. They're for display only.
- **Hyperspectral thumbnails** are pseudo-RGB composites.

## Experimental structure (typical, verify per export)
- **Plants sit in trays** at fixed slots and pass through the stations in rounds.
- **Design factors** (genotype, treatment, replicate) are in each sensor's design table and in the plant label code.
- **What the treatment means isn't part of the format.** Ask the owner.

## [inferred] To confirm with the APPL team
- Whether RGB2's mm scale is known to be wrong, and the correct scale.
- The exact FC1 protocols per round slot, and what `L1..L4`/`Lss`/`D1..D3` correspond to.
- Why rows get blanked in MSC1 (the invalid-source flag).
- Tare handling for weights.
- Timezone of timestamps.
- Whether the sensors not seen yet (RGB1, FC2, IR1, MSC2, ROOT) follow the same table conventions.
