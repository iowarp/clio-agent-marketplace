---
name: forecast-probabilities
title: Forecast Probabilities and Scores
description: Answer forecast questions with uncertainty - ensemble exceedance probabilities at a place, AI forecasts with their checkpoint and licence, cyclone tracks scored against best tracks, and forecast scores by lead time.
keywords:
- level:L1
- weather
- forecast
- ensemble
---

# Forecast probabilities and scores

## A probability at a place

"What is the chance of more than X in the next days?" is an ensemble
question, not a deterministic one.

1. `ensemble_fetch` the latest ensemble run for the point (ECMWF ENS open
   data, no key). Say which run (date and cycle) you used.
2. `exceedance` with the threshold and the accumulation window the person
   meant. Accumulated variables are accumulated from the run start: take
   differences over the window, not single steps.
3. Report the probability as the fraction of members, the number of
   members, and the spread (the members' range or quantiles). A plume chart
   of the members against the threshold shows it.

For a single deterministic forecast at a place, ECMWF's `ecmwf-open-data`
skill is the shortest path.

## AI forecasts

`ai_forecast` runs a pretrained model from initial conditions you choose
(reanalysis for a past event, a recent analysis for now). Every result
records the model, its checkpoint and that checkpoint's licence, and the
initial-condition source and time: report them. A model that needs a GPU
the machine lacks is refused with a reason; say so rather than switching
models silently.

## Cyclone tracks

`tc_track` follows lows in a forecast with an explicit backend (the
TempestExtremes node tracker on CPU, or Earth2Studio's trackers on a CUDA
GPU). `ibtracs_fetch` gets the best track; `track_score` gives position and
intensity error by lead time. Match storms by time and distance, and say how.

## Scores

`score` gives RMSE, anomaly correlation and CRPS by lead time and region
against a reference (reanalysis or analysis). Score every run being compared
on the same verification grid, times and region, and state the reference.
`station_fetch` and `station_verify` compare forecasts with station
observations; give the number of stations and the period.
