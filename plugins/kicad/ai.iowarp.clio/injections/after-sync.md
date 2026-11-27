---
name: after-sync
event: tool_result
tool: kicad_pcb_sync_from_schematic
title: Before and during placement
description: When the board is synced from the schematic, remind the agent of the steps that come before placement, and that placement is judged and adjusted in the board view.
active: true
---
{% if not tool.is_error %}Placement builds on two earlier steps of the board pipeline: each IC's symbol and footprint pins checked against its datasheet (`datasheet-pin-check`), and the power stages and filters simulated on the spice connector (offer it with `offer_plugin` when it is not on); a step you skip, tell the person with what stays unverified. Then judge each placement pass in the board view (`view_board`): `set_layers` to the courtyards and Edge.Cuts, `focus` on the parts you placed, look with its `capture` (or `look_at_view`), and move what is wrong by hand with `pcb_move_footprint`, `pcb_set_footprint_layer` and `pcb_set_footprint_locked`.{% endif %}
