---
name: scientific-data-analysis
title: Analyze Scientific Data Against Its Actual Question
description: Match an analysis approach to the data's actual structure and the question being asked, and state every processing step applied to raw data before reporting a result.
keywords:
- level:L0
- scientific-method
---

State the data's structure before choosing an analysis: sample size, whether
observations are independent or grouped/repeated (e.g., multiple
measurements per specimen or subject), and the presence of censored data
(observations stopped before the event of interest) — a method that assumes independence applied to grouped data
understates uncertainty.

Record every processing step applied between raw data and reported result:
outlier removal (with the criterion used), smoothing or filtering,
normalization, and unit conversion. A result should be reproducible from the
raw data plus this stated processing chain.

Match the specific statistical method to the question (`statistics`) and
report uncertainty (`uncertainty-quantification`) as part of the result, not
as an afterthought — a data analysis that reports only a point estimate or a
best-fit line without its uncertainty is incomplete for a scientific claim.

Return the data structure and processing chain applied, the analysis method
and result, and the uncertainty and assumptions behind it.
