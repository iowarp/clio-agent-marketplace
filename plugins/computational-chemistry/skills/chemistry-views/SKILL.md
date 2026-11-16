---
name: chemistry-views
description: Use when presenting chemistry results to the person - an optimization, frequencies or a spectrum, a reaction energy across methods, a screening of many materials, a crystal - to choose the view that suits the data and link it to the structure so their selection comes back as data.
keywords: [chemistry, visualization, chart, spectrum, energy diagram, viewer, level:L1]
---

# Which view for which result

These are suggestions; the person's question decides. Structures belong in the molecular
viewer (an application view); everything that works over result files belongs in charts
and tables.

| Result | View | Linked by |
| --- | --- | --- |
| An optimization | energy and largest force against step | step → the viewer's frame |
| Frequencies, IR | a stick or broadened spectrum, and the frequency table | mode → the viewer plays that mode |
| A spectrum to compare (XANES, IR) | overlay with the reference or measurement, normalized and aligned | the site or structure each spectrum came from |
| Reaction energies across methods | an energy diagram, one series per method, species in reaction order | species → its structure |
| A scan (dihedral, distance) | energy against the coordinate | point → that structure |
| Screening many materials | a scatter of two properties plus a sortable table, shared selection | row → its structure |
| A crystal | the structure with its unit cell (and a supercell when periodicity matters) | atom → its site |

Label axes with quantity and unit. Put the method in the legend. Build each chart from a
file (CSV) the calculation wrote, so the chart and the numbers in the reply agree. When a
view updates while calculations run (a diagram filling in per species), say so, and
report the final numbers from the results, not from the picture.
