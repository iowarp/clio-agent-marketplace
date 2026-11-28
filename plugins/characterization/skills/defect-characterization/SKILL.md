---
name: defect-characterization
title: Synthesize Defect Evidence Across Characterization Techniques
description: Combine XCT, fractography, and microstructural evidence into one defect population/root-cause finding rather than reporting each technique's result in isolation.
keywords:
- level:L1
- characterization
---

This skill applies once individual characterization results (`xct`,
`fractography`, `microstructure`) are
available and the question is what they say together about a part's defect
state or a failure's root cause. It synthesizes; it does not replace running
the individual techniques.

Findings cross-check across techniques where they should agree: a pore
identified as the fatigue-initiation site by fractography should be
findable, in size and location, in the XCT pore-population data for that
specimen. Agreement strengthens the finding, and disagreement (e.g., a
fractography-identified initiator not present in the XCT data) is itself a
finding, not a discrepancy to quietly resolve.

The defect population relates to the manufacturing/processing record
(`additive-manufacturing`, `am-process-parameters`): the defect type and
severity are either consistent with the known process parameters or an
anomaly in their own right.

The synthesized finding (population characteristics, cross-technique
agreement or disagreement, consistency with the process record) is what
`defect-driven-fatigue` takes when the question is fatigue life.
