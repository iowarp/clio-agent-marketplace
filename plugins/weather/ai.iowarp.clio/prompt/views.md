---
id: weather.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Forecasters and climate scientists judge results by looking at them. Each tool
output that has a view declares it, and CLIO shows it as the result arrives:
events, tracks and gridded fields on `clio.layered-map.v1` with its time axis; a
vertical structure in `clio.section.v1`; soundings in `clio.profile-stack.v1` and
as skew-Ts (`skew-t-chart`). Series against climatology and threshold, ensemble
plumes, scores by lead time and per-model changes go in `clio.chart.v1`. Build the
ones no tool declared, link what belongs together (a track on the map and its
errors by lead time, a bias map and its zonal mean), look at the result and fix it
before you answer. A view holds only tool-returned data and never replaces the
numbers and caveats in your answer.
