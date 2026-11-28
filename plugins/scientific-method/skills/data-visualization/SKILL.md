---
name: data-visualization
title: Choose and Execute a Scientific Figure That Makes the Comparison Visible
description: Use when choosing and drawing a chart, to match its type and encoding to the comparison, with labelled units, visible uncertainty and a self-contained caption.
keywords:
- level:L0
- visualization
- figures
---

## The comparison decides the chart

Each comparison has charts that make it visible:

- distributions between conditions: box, violin or probability plots;
- a trend against a controlled variable: points with a fit and its band;
- a relationship between two continuous variables: a scatter plot with a fit;
- composition or ranking: ordered bars.

A chart chosen before the comparison is named usually shows the data without
making the claim visible.

The representation follows the data's structure. Censored observations
(values known only to exceed or fall below a limit, such as tests stopped
before the event) drawn as ordinary points read as events; data spanning
orders of magnitude needs a log axis, and the reader needs to know it is one;
repeated measurements of one unit read as independent unless grouped visibly.

A log or truncated axis, or an omitted point, can make an effect look stronger
or weaker than the statistics (`statistics`) support.

## What makes a figure readable

- Axes labelled with quantity and units, and the scale (linear, log,
  semi-log) evident.
- Uncertainty on the figure itself: error bars or a band, with the caption
  saying what they represent (standard deviation, standard error, a
  confidence interval) and the sample size.
- A self-contained caption: what was measured, under which conditions, the
  sample size, and what the figure shows.
- Fonts, line weights and markers legible at the final printed or displayed
  size.
- The plotting script and its input files kept with the figure, so it can be
  regenerated.
