---
id: earthscope.views
section: domain
when: {"tools": ["create_a2ui_surface"], "session": "root"}
---
A view helps more than prose when it sits right after the evidence it shows: a small map after resolving a region, the `earthscope-stations` map and picker after ranking stations (catalog skill `a2ui-catalog-earthscope-stations`), a data-backed chart after fitting a series (`present-interactive-analysis`). A static plot is an export, not the default view of a series. Reusing a surface id updates it in place. A view holds only tool-returned rows and does not replace the numbers or caveats.
