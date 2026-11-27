---
name: pcb-routing
description: "Route a KiCad board with KiCad MCP Pro: power and critical nets by hand with the routing tools, FreeRouting for the rest, then zones and DRC until clean."
---

# PCB routing

Use this skill once placement is settled. Route in this order; check after each step.

1. **Rules first.** Set net classes for power, high-current and signal nets
   (`route_set_net_class_rules`, `pcb_set_design_rules`), and the stackup
   (`pcb_get_stackup`, `pcb_set_stackup`). Widths follow the current each net carries.
2. **By hand, what matters most.**
   - Power: wide tracks or a pour from the regulator to its loads.
   - Decoupling: each capacitor to its pin and to ground with the shortest loop; a via to the
     ground plane right at the pad.
   - Differential pairs (USB, Ethernet) with the pair tools, matched in length, over an
     unbroken reference plane.
   - Crystals and sensitive analog: short, away from switching nodes.
   Use `route_single_track`, `route_from_pad_to_pad` and `pcb_add_via`.
3. **FreeRouting for the rest.** `route_autoroute_freerouting` routes what is left. The
   server installs FreeRouting and the Java runtime it needs by itself the first time (or
   uses Docker), and the result says what it installed. When it cannot, the result says why
   and how the person installs it: routing a whole board by hand is slow and error-prone, so
   do not start it on your own. Ask once with `ask_user`, giving the reason and the steps
   from the result: install it and route again, or route by hand.
4. **Review what the autorouter did, and correct it.** An autorouter connects every net but
   does not judge: look at the routes in the board view (`set_layers` to the copper layers,
   `focus` on the power nets, decoupling, the pairs and dense areas, then its `capture` or
   `describe_region`) and read the tracks (`pcb_get_tracks`, `pcb_get_vias`). Look for power tracks narrower than their current needs, decoupling loops
   that wander away from their pins, a differential pair split or routed apart, copper or vias
   inside an antenna keepout, long detours and needless vias, acute angles and stubs. Delete
   what is wrong (`pcb_delete_items`) and route it by hand, then look again.
5. **Zones.** Add ground (and power) pours (`pcb_add_zone`), then `pcb_refill_zones`.
6. **DRC until clean.** `run_drc`; fix each violation at its cause, never by loosening a rule
   without saying why; run again until there are none or every remaining one is explained.

Record completion, vias and total track length after routing, as you did for placement.
