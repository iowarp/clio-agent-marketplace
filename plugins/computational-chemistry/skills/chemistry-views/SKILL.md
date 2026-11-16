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

A view here is interactive: a chart or table in the conversation drawn from the active
A2UI catalog (`present-interactive-analysis`), or a dashboard with the structure view
beside its charts (`create-dashboard`, and `burette-views` "In a dashboard" for the
link). Its "linked by" column only works in such a view: a rendered image (a matplotlib
PNG) cannot carry the person's pick back or follow new results, so it is for when they
ask for a figure file.

Label axes with quantity and unit. Put the method in the legend. Build each chart from a
file (CSV) the calculation wrote, so the chart and the numbers in the reply agree. A view
that fills in while calculations run (a diagram per species) binds that file at
`@latest` (`create-dashboard`), and each finished result adds its row to the file; say
that it updates, and report the final numbers from the results, not from the view.
