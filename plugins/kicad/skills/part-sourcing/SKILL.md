---
name: part-sourcing
description: "Load before searching for, choosing, comparing or pricing parts with the KiCad connector: which part catalogs answer, what to do when one fails or a part is scarce, and how the person adds catalog keys through a card."
---

# Finding and sourcing parts

## Search by spec

Search by what the design needs, not by a guessed part number: `lib_search_parametric` with
filters (`{name, op, value, unit}`; values compare in SI units), one part's full sheet with
`lib_get_component_specs`, candidates side by side with `lib_compare_parts`. Open `view_parts`
with your shortlist in `candidates` when the person should choose; their pick binds the part
(`lib_bind_part_to_symbol`) and arrives as context.

## The catalogs, and what their answers mean

Parts search uses jlcsearch (JLCPCB's catalog, no key) unless the person added keys for
Nexar, DigiKey or Mouser. Every sourcing result names the sources that answered, and a result
from a failed or limited search lists the sources that could be configured and what each
adds. Stock and price are what the answering sources report, not what exists: "out of stock
at jlcsearch" means only that, and "stock not reported by jlcsearch" means it is unknown, not
zero. A web search finds candidate parts and datasheets, but it does not give stock or a
price you can order at.

## When a catalog failed and a key would change the answer

Ask once, before falling back to other means: `offer_plugin` with plugin `kicad`, your reason
(what you are looking for and which sources failed), and `needs` set to the keys of the
sources you want (the listing's `optional_needs` names them). The person types keys into the
card, never into the chat; never ask for a key in a message. If they choose Not now, carry on
with what is available (other sources, datasheets, a web search for candidates) and say in
your answer which sources you could not ask and what that leaves unconfirmed; do not ask
again for the same keys in this conversation.

## When a part is scarce

A passive or other part with many equivalents is yours to swap for an in-stock one; say what
you chose. A core part, one the design is built around (the processor or module, a sensor the
brief names, the regulator, the connectors), that is out of stock, or stocked below what the
build needs, is the person's decision: they know whether they can wait, pay more or redesign.
Ask once with `ask_user` (a choice), saying which sources you asked and what each reported,
and offer what is open:

- add a part catalog (Nexar, DigiKey, Mouser), which you then raise with `offer_plugin`;
- keep the part and order it when it is back, accepting the wait;
- search further: other packages, pin-compatible parts, other families, or a part with no
  KiCad symbol (generate it from the datasheet, `datasheet-pin-check`);
- change the requirement (another kind of sensor, another module).

Carry on with work the answer does not change while you wait.
