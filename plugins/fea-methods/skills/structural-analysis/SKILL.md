---
name: structural-analysis
title: Reason Over Structural Response Under Load
description: Connect a loading scenario to the structural response mode it actually produces — stiffness, stability, or strength-limited — before selecting an analysis type.
keywords:
- level:L1
- fea-methods
---

Structural questions differ in the response they are about: stiffness
(deflection under load), stability (buckling), or strength (yield/ultimate
capacity, fatigue). The analysis type, mesh density, and material model
needed differ for each, and a study set up for one does not automatically
answer another.

The load path is how load enters the structure, how it is carried to the
supports, and where it concentrates (fillets, holes, section changes,
joints). A global result (maximum stress) without the load path cannot
explain why that location governs.

A linear-elastic structural analysis is valid for stress below yield and
small deflection; large deflection, contact, material plasticity and buckling
past the linear regime need `finite-element-analysis`'s nonlinear treatment.
A linear result outside its validity range overstates margin or understates
deflection.
