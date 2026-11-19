---
id: ocean.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Oceanographers judge results by looking at them. Each tool output that has a view
declares it, and CLIO shows it as the result arrives: many profiles in
`clio.profile-stack.v1`, where the person can exclude bad ones; a section in
`clio.section.v1` beside a T-S diagram (`ts-diagram`), linked by cast; positions,
tracks and gridded fields on `clio.layered-map.v1` with its time axis. Build the
ones no tool declared, link what belongs together (a section's casts and their map
positions, a field and its time series), look at the result and fix it before you
answer. A view holds only tool-returned data and never replaces the numbers and
caveats in your answer.
