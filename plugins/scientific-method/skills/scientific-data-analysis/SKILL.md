---
name: scientific-data-analysis
title: Analyze Scientific Data Against Its Actual Question
description: Match an analysis approach to the data's actual structure and the question being asked, and state every processing step applied to raw data before reporting a result.
keywords:
- level:L0
- scientific-method
---

The data's structure constrains the analysis: sample size, whether
observations are independent or grouped/repeated (e.g., multiple measurements
per specimen or subject), and the presence of censored data (observations
stopped before the event of interest). A method that assumes independence
applied to grouped data understates uncertainty.

A result is reproducible from the raw data plus its processing chain: outlier
removal (with the criterion used), smoothing or filtering, normalization, and
unit conversion.

The statistical method matches the question (`statistics`), and uncertainty
(`uncertainty-quantification`) is part of the result, not an afterthought: a
data analysis that reports only a point estimate or a best-fit line without its
uncertainty is incomplete for a scientific claim.
