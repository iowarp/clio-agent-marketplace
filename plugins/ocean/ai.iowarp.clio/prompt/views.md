---
id: ocean.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Oceanographers judge results by looking at them, so show the evidence as a view right after computing it: a section with `clio.section.v1` beside a T-S diagram (`ts-diagram`), linked by cast; many profiles in `clio.profile-stack.v1`, where the person can exclude bad ones; positions, tracks and gridded fields on `clio.layered-map.v1` with its time axis. Reference the files you wrote rather than copying rows. A view holds only tool-returned data and never replaces the numbers and caveats in your answer.
