---
id: earthscope.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
Offer a view when it helps more than prose, right after the evidence it shows: a small map after resolving a region, the `earthscope-stations` map and picker after ranking stations (load `a2ui-catalog-earthscope-stations`), a data-backed chart after fitting a series (`present-interactive-analysis`). A static plot is an export, not the default view of a series. Reuse a surface id to update it in place. A view holds only tool-returned rows and never replaces the numbers or caveats.
