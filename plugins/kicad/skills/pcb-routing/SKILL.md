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
3. **FreeRouting for the rest.** `route_autoroute_freerouting` routes what is left. It needs
   Java with the FreeRouting JAR, or Docker with its image; when neither is present, say so
   and route by hand.
4. **Zones.** Add ground (and power) pours (`pcb_add_zone`), then `pcb_refill_zones`.
5. **DRC until clean.** `run_drc`; fix each violation at its cause, never by loosening a rule
   without saying why; run again until there are none or every remaining one is explained.

Record completion, vias and total track length after routing, as you did for placement.
