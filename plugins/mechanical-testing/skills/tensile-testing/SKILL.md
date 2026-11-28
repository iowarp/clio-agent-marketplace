---
name: tensile-testing
title: Run and Interpret a Tensile Test
description: Extract baseline material behavior from a tensile test with its rate, geometry, and extensometry stated, and distinguish engineering from true stress-strain.
keywords:
- level:L1
- mechanical-testing
---

Yield and ultimate strength are rate-sensitive for many materials and
temperatures, so a comparison across tests needs matched strain rates or
crosshead speeds. Specimen geometry (gauge length/diameter or cross-section)
per the governing standard (ASTM E8/E8M) makes reduction-of-area and
elongation results comparable to other reported values.

Engineering stress-strain (based on original cross-section, what the raw
load-displacement data gives directly) differs from true stress-strain (based
on instantaneous cross-section, needed for input to a finite-element material
model past necking): engineering values as an FE material input past the
necking point produce an incorrect large-strain response.

Each property has an extraction method: elastic modulus (sensitive to
extensometer resolution and specimen alignment), yield strength (0.2% offset
or another method), ultimate strength, elongation, and reduction of area. A
property extracted from a crosshead-displacement proxy rather than a direct
extensometer is biased by compliance in the load train, especially modulus
and yield.
