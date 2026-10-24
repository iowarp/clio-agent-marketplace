---
name: data-visualization
title: Choose and Execute a Scientific Figure That Makes the Comparison Visible
description: Pick the chart type and encoding from the comparison being made, then execute it with labelled axes and units, visible uncertainty and a self-contained caption, without implying more precision or a stronger effect than the data supports.
keywords:
- level:L0
- visualization
- figures
---

## Choose from the comparison

Name the comparison before choosing a chart:

- distributions between conditions: box, violin or probability plots;
- a trend against a controlled variable: points with a fit and its band;
- a relationship between two continuous variables: a scatter plot with a fit;
- composition or ranking: ordered bars.

A chart chosen before the comparison is named usually shows the data without
making the claim visible.

Match the representation to the data's structure. Censored observations
(values known only to exceed or fall below a limit, such as tests stopped
before the event) must be marked distinctly, never drawn as ordinary points;
data spanning orders of magnitude needs a log axis, stated as such; repeated
measurements of one unit should be grouped visibly.

Check the figure's claim against the statistics (`statistics`): a log or
truncated axis, or an omitted point, can make an effect look stronger or
weaker than the data supports.

## Execute it

- Label every axis with quantity and units, and state the scale (linear, log,
  semi-log).
- Show uncertainty on the figure itself: error bars or a band, with the
  caption saying what they represent (standard deviation, standard error, a
  confidence interval) and the sample size.
- Write a caption that makes the figure self-contained: what was measured,
  under which conditions, the sample size, and what the reader should
  conclude.
- Keep fonts, line weights and markers legible at the final printed or
  displayed size.
- Keep the plotting script and its input files with the figure so it can be
  regenerated.

## Return

The figure with its comparison, chart type and encoding, labelled axes with
units, visible uncertainty, a self-contained caption, and the script and
inputs that produced it.
