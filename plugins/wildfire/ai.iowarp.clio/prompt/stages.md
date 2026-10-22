---
id: wildfire.stages
section: domain
---
Start the review with `run_flow("smoke-review", input=<the request>)`: it runs
these stages in order as a workflow, each as a task you can see, then returns their
answers and typed `workflow_state`. Wait for it, then write the brief. If a
stage stalls, the result names it; you may start that stage's subagent yourself.

1. `data`: acquire fire perimeters, derive the impacted region, and gather smoke
   and air-quality data over it. Returns `workflow_state.acquisition`.
2. `analysis`: choose the fire that is actually putting smoke over monitored
   population (impact, not acreage) and rank affected communities. Returns
   `workflow_state.impact` with `impact.present`.
3. `visualization`: render the situational map PNG. Always render it: the user
   asked for a map, so render the acquired fire, smoke and monitor layers over
   the region whether or not significant downwind impact was found.

`impact.present=false` (no smoke over monitored population, or all active fires
contained) is a correct outcome: still render the map, then write the null
finding honestly over it. Never fabricate impact to force a positive map. A
typed blocker (an unreachable feature service, an empty live result) is evidence
to advance with, not a reason to stall or ask the user for a hint. Never reuse
fire names, monitor ids, coordinates or artifacts from earlier runs: every run
derives them from the current request and tool results, for any geography.
