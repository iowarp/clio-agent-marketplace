---
name: defect-characterization
title: Synthesize Defect Evidence Across Characterization Techniques
description: Combine XCT, fractography, and microstructural evidence into one defect population/root-cause finding rather than reporting each technique's result in isolation.
keywords:
- level:L1
- characterization
---

Use this skill once individual characterization results (`xct`,
`fractography`, `microstructure`) are
available and the question is what they say together about a part's defect
state or a failure's root cause. It synthesizes; it does not replace running
the individual techniques.

Cross-check findings across techniques where they should agree: a pore
identified as the fatigue-initiation site by fractography should be
findable, in size and location, in the XCT pore-population data for that
specimen — agreement strengthens the finding, and disagreement (e.g., a
fractography-identified initiator not present in the XCT data) is itself a
finding worth reporting, not a discrepancy to quietly resolve.

State the defect population's relationship to the manufacturing/processing
record (`additive-manufacturing`, `am-process-parameters`): whether the
defect type and severity are consistent with the known process parameters,
or are an anomaly to report as such.

Return the synthesized defect finding: the population characteristics,
cross-technique agreement or disagreement, and its consistency with the
process record — handed to `defect-driven-fatigue` when the question is
fatigue life.
