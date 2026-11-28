---
name: statistics
title: Choose and Report a Statistical Test or Fit Correctly
description: Match a statistical test or distribution fit to the data's actual properties, and report its assumptions and limitations alongside the result.
keywords:
- level:L0
- scientific-method
---

A method has assumptions: normality (or the specific distribution assumed:
lifetimes, sizes and other positive, skewed quantities are often better
described by a lognormal or Weibull distribution than a normal one),
independence of observations, and equal variance across groups being compared.
A t-test or linear regression applied where these fail can produce a misleading
p-value or confidence interval.

A comparison is defined by the test used and its p-value against a significance
threshold set in advance (one chosen after seeing the result tests nothing); a
curve or distribution fit by its fitting method (least squares, maximum
likelihood) and goodness-of-fit measure. Censored observations (an event not yet
seen when observation stopped) need a method that uses them as censored, such
as maximum likelihood with censoring; dropping them, or treating them as
events, biases the fit.

Statistical significance is not practical significance: a statistically
significant difference with a small effect size may not matter for the decision
at hand, which a p-value alone does not tell the reader.
