---
name: create-diagram
title: Create Diagram
description: Choose, compose and review diagrams from a person's material. Mermaid's component entry supplies the complete supported-family inventory, syntax and examples; this skill covers the authoring workflow.
---

Start with the relationships the reader needs to understand. A protocol has
participants and ordered messages; an ER model has entities and cardinalities;
a lifecycle has states and transitions; commit history has ancestry; a grammar
has accepted token sequences; a hierarchy has containment. Choose the notation
that preserves that meaning. A diagram is optional: prose, a table or a list
can answer better.

## One authority for the component

The active A2UI catalog's **`clio.mermaid.v1` entry** contains the complete
supported-family inventory, syntax, runnable examples, notation variants and
CLIO viewer behaviour. Load its exact schema in the same batch as any needed
layout components:

```text
load_skill("a2ui-catalog-clio-workspace", files=[
  "catalog.json#/components/clio.mermaid.v1",
  "catalog.json#/components/Column"
])
```

Use the catalog skill actually declared for this session; the example names
CLIO's workspace catalog. The returned `x-clio-authoring` is guidance, not a
property to copy into a component payload. It covers all supported families,
not only flowcharts/sequences. Choose the relevant family and use its syntax;
there is no requirement to render every family. No additional syntax reference
from this skill is needed. Mermaid remains the source language and component
name; the bundled rendering library is an implementation detail.

The declared A2UI surface tools render diagrams, including diagrams embedded in
a short chat explanation. A `mermaid` fenced block displays source code; it does
not create the visual. Mermaid source is what a request for Mermaid code or a
Markdown export asks for. Without rendering there is only source, not a rendered
diagram. For a composed saved report, `create-dashboard` covers publication and revision.
The catalog is the authority for source/artifact inputs, controls, themes,
navigation and limitations; component properties come from it, not from
library APIs.

## Author from evidence

The facts that must survive are the entities and attributes, edge direction,
branch conditions, message order, optionality, multiplicity, dates or
ownership; a small checklist against the supplied material catches what a
draft drops. Uncertainty and synthetic examples are marked as such; stages,
measurements, filenames and chronology come from the material.
Stable IDs are separate from display labels. Preserved source text lets a
later revision change the diagram rather than rebuild it from a screenshot.
Source statements need actual newlines. The component entry includes a complete
JSON payload showing one level of newline encoding; serialized once, the
document leaves no literal backslash-n separators in the source value.

Give each diagram the space its relationships need. Full width, equal columns,
uneven columns and a vertical report are all options. Separate independent
subjects when useful, while keeping views needed for a comparison together.
Keep quantitative evidence in data views when filtering, units or shared
selection matter; diagrams and custom HTML/SVG are available for explanations
that benefit from them.

Folder links are intentional actions, not inferred from filenames or node
names. The catalog's explicit `workspace-folder:` targets point at real folders
in the workspace; a conceptual tree does not imply real files exist.

## Review the authored result

`review-visual-presentation` covers rendered review. The captured image of the
published artifact at the docked width, an expanded view when needed, and
every relevant view (not just the first tab) show headings, labels, legends and
arrows as well as the diagram bounds. Source visibility or a successful render
does not establish readability.

Compared with the evidence checklist, the rendered relationships show missing
conditions, reversed arrows, omitted siblings, undefined grammar productions,
clipped text or unreadable scaling; a fresh capture shows whether a fix took. A
difficult relationship simplified away to make syntax pass is lost from the
diagram. An unavailable capture and a parser error are different failures.
A renderer gallery tests the renderer; acceptance requires the model's own
authored artifact and its actual captured pixels.

Each normal and exceptional path runs from its start to its outcome, and
alternatives occur at the decision they represent: a failed or cancelled path
that first performs actions reserved for success is wrong. A module
dependency, a call and a data transfer are different relationships; a label
says which one an arrow means, where proximity or module names would imply a
call or ownership relationship.
The smallest labels at the captured viewing size decide readability; lower
label density, a split subject or an adjusted view fix labels that are too
small, and fresh pixels show the result. All nodes fitting does not make a
captured diagram readable.
