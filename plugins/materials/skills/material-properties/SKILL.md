---
name: material-properties
title: State and Bound a Material Property Claim
description: Attach a material property to its measurement method, condition, and source class before it is used in a design or simulation decision.
keywords:
- level:L1
- materials
---

A property has a source class: measured (with method and specimen state),
datasheet minimum/typical (a statistical bound, not a measured value for the
specific lot), or model-predicted (with the model's own assumptions). These
are not interchangeable, and a design decision rests on one of them.

A property holds under the condition it was obtained at: temperature, strain
rate, environment, orientation (for anisotropic material), and specimen
geometry/size. Yield strength, fatigue limit, and fracture toughness are all
condition-sensitive, so a property without its condition is incomplete.

Some properties are intrinsic to the material composition/phase state;
others are extrinsic (geometry- or process-dependent, like fracture toughness
in thin sections, or fatigue strength in the presence of surface roughness or
porosity). Extrinsic properties do not transfer between parts with different
geometry or processing history.
