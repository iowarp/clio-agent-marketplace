---
name: manufacturability
title: Check a Design Against Its Manufacturing Process Constraints
description: Evaluate whether a proposed geometry — often a topology-optimized one — can actually be produced by the intended process, before treating it as a manufacturable part.
keywords:
- level:L1
- manufacturing-processes
---

A design is buildable when it meets the process-specific geometric
constraints: minimum feature size and wall thickness, maximum unsupported
overhang angle, enclosed/trapped-powder volumes (critical for powder bed
fusion: trapped powder cannot be removed and adds mass and potential
contamination), and minimum hole/channel diameter for the intended process.

A topology-optimized geometry is a design proposal, not a manufacturability
guarantee: complex organic geometry commonly produced by topology optimization
frequently violates overhang and trapped-volume constraints, and reconciling
the two is a distinct step (manufacturing-constrained optimization or manual
redesign), not automatic.

"Manufacturable" means as much as the checks actually performed. A violation
is resolved by redesign, added supports, or an accepted process risk, or it
remains open.
