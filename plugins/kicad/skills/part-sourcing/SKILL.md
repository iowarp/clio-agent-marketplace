---
name: part-sourcing
description: "Searching for, choosing, comparing or pricing parts with the KiCad connector: which part catalogs answer and what their answers mean, adding catalog keys through a card, and what is open when a part is scarce."
---

# Finding and sourcing parts

## Search by spec

`lib_search_parametric` searches by what the design needs, with filters (`{name, op, value,
unit}`; values compare in SI units); `lib_get_component_specs` gives one part's full sheet and
`lib_compare_parts` sets candidates side by side. `view_parts` with a shortlist in
`candidates` lets the person choose; their pick binds the part (`lib_bind_part_to_symbol`) and
arrives as context.

## The catalogs, and what their answers mean

Parts search uses jlcsearch (JLCPCB's catalog, no key) unless the person added keys for
Nexar, DigiKey or Mouser. Every sourcing result names the sources that answered, and a result
from a failed or limited search lists the sources that could be configured and what each
adds. Stock and price are what the answering sources report, not what exists: "out of stock
at jlcsearch" means only that, and "stock not reported by jlcsearch" means it is unknown, not
zero. A web search finds candidate parts and datasheets, but it does not give stock or a
price you can order at.

## Catalog keys

`offer_plugin` with plugin `kicad`, a reason (what you are looking for and which sources
failed) and `needs` set to the sources' keys (the listing's `optional_needs` names them) shows
the person a card where they type the keys. The card stores them as the connector's secrets;
a key typed in the chat stays in the conversation, so never ask for a key in a message. A
person who chose Not now on the card has answered for this conversation.

## When a part is scarce

A passive or another part with many equivalents swaps for an in-stock one. A core part, one
the design is built around (the processor or module, a sensor the brief names, the regulator,
the connectors), out of stock or stocked below what the build needs, turns on what only the
person knows: whether they can wait, pay more or redesign. What is open:

- add a part catalog (Nexar, DigiKey, Mouser) through `offer_plugin`;
- keep the part and order it when it is back, accepting the wait;
- search further: other packages, pin-compatible parts, other families, or a part with no
  KiCad symbol (generated from the datasheet, `datasheet-pin-check`);
- change the requirement (another kind of sensor, another module).
