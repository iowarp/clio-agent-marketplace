---
id: weather.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Forecasters and climate scientists judge results by looking at them, so show the evidence as a view right after computing it: events, tracks and gridded fields on `clio.layered-map.v1` with its time axis; a vertical structure in `clio.section.v1`; soundings in `clio.profile-stack.v1` and as skew-Ts (`skew-t-chart`); series against climatology and threshold, ensemble plumes and per-model changes as `clio.chart.v1`. Reference the files you wrote rather than copying rows. A view holds only tool-returned data and never replaces the numbers and caveats in your answer.
