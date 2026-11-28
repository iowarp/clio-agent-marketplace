---
name: additive-manufacturing
title: Reason Over Additive Manufacturing Process Families and Their Consequences
description: Name the AM process family precisely and trace it to the defect and anisotropy population it characteristically produces, before any process-specific reasoning.
keywords:
- level:L1
- manufacturing-processes
---

AM process families (powder bed fusion by laser or electron beam, directed
energy deposition, binder jetting, material extrusion, sheet lamination)
differ in defect mechanisms, achievable tolerances, and applicable materials,
and these do not transfer across families.

Layer-wise build-up is generic to all AM; the energy source, feedstock form,
and consolidation mechanism are family-specific. Anisotropy from the build
direction and a dependency of final properties on process parameters are
near-universal across AM; the specific mechanism producing them is not.

Parameter-level reasoning (the full parameter set, and for laser powder bed
fusion the melt-pool regime and defect mechanisms) is in
`am-process-parameters`.
