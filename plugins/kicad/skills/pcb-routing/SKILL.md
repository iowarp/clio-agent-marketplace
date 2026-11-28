---
name: pcb-routing
description: "Route a KiCad board with KiCad MCP Pro: rules and stackup, power and critical nets with the hand-routing tools, FreeRouting, reviewing what an autorouter made, zones and DRC."
---

# PCB routing

## Rules and stackup

Net classes for power, high-current and signal nets (`route_set_net_class_rules`,
`pcb_set_design_rules`) and the stackup (`pcb_get_stackup`, `pcb_set_stackup`) set the widths
and clearances the routers and DRC use. A track's width follows the current its net carries.

## The nets that matter most

- Power: wide tracks or a pour from the regulator to its loads.
- Decoupling: each capacitor to its pin and to ground with the shortest loop; a via to the
  ground plane right at the pad.
- Differential pairs (USB, Ethernet), with the pair tools, matched in length, over an unbroken
  reference plane.
- Crystals and sensitive analog: short, away from switching nodes.

`route_single_track`, `route_from_pad_to_pad` and `pcb_add_via` route by hand.

## FreeRouting

`route_autoroute_freerouting` routes what is left. The server installs FreeRouting and the
Java runtime it needs by itself the first time (or uses Docker), and the result says what it
installed. When it cannot, the result says why and how the person installs it. Routing a
whole board by hand is slow and error-prone, a cost the person may prefer to avoid by
installing FreeRouting.

## What an autorouter leaves

An autorouter connects every net but does not judge them. The board view shows its routes
(`set_layers` to the copper layers, `focus` on the power nets, decoupling, the pairs and dense
areas, then its `capture` or `describe_region`), and `pcb_get_tracks` and `pcb_get_vias` read
them. Its usual faults: power tracks narrower than their current needs, decoupling loops that
wander away from their pins, a differential pair split or routed apart, copper or vias inside
an antenna keepout, long detours and needless vias, acute angles and stubs.
`pcb_delete_items` removes a bad track for routing by hand.

## Zones and DRC

`pcb_add_zone` adds ground (and power) pours; `pcb_refill_zones` fills them. `run_drc` lists the
violations. Loosening a rule clears a violation from the report, not from the board.
