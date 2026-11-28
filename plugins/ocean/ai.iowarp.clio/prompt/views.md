---
id: ocean.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Oceanographers judge results by looking at them. Each tool output that has a view
declares it, and CLIO shows it as the result arrives: many profiles in
`clio.profile-stack.v1`, where the person can exclude bad ones; a section in
`clio.section.v1` beside a T-S diagram (`ts-diagram`), linked by cast; positions,
tracks and gridded fields on `clio.layered-map.v1` with its time axis. Views no
tool declared can be built; linked views show what belongs together (a section's
casts and their map positions, a field and its time series); and a rendered view
can be looked at and corrected before the answer. A view holds only
tool-returned data and does not replace the numbers and caveats in the answer.
