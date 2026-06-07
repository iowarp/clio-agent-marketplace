---
id: wildfire-smoke-impact-review
title: Wildfire Smoke Impact Review Agent
version: 0.1.0
description: Finds an active wildfire impacting people downwind by fusing live fire perimeters, smoke forecast, and air-quality data, and renders a situational map.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/data.md
  - experts/fire_discovery.md
  - experts/geography.md
  - experts/smoke_forecast.md
  - experts/air_quality.md
  - experts/analysis.md
  - experts/downwind_impact.md
  - experts/visualization.md
  - experts/synthesis.md
defaults:
  prompt_profile: heavy
---

# Wildfire Smoke Impact Review Agent

A hazard-domain agent that answers "which active wildfire is putting smoke over
people right now, and who is worst affected?" by fusing three independent live
NDP feature services — interagency fire perimeters, the NWS smoke forecast, and
AirNow air-quality monitors — and rendering one situational map.

The agent uses the **domain-grouped** topology proven on the EarthScope case:
the orchestrator delegates to domain experts (data acquisition, geography,
impact analysis, visualization, synthesis), and the data domain delegates to
independent acquisition sub-experts. Routing is by typed workflow state and
explicit child completion, never by free-text string matching. The interesting
fire is selected by **downwind impact**, not by perimeter size, and a
"no significant impact right now" result is a correct, reachable answer.
