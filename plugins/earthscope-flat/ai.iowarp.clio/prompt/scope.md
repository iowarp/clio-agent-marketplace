---
id: earthscope-flat.scope
section: domain
---
## Do what THIS request asks — no more, no less

This is a multi-turn session. Spawn ONLY the pipeline stages the current request
needs, then write the answer. The stages are means, not a fixed script:

- Asks only whether data EXISTS, or to FIND / LIST stations near a place → spawn
  `geospatial` → `ndp` (discover + rank), then answer. Do NOT stage, profile,
  or plot.
- Asks to STAGE / explore / inspect a station's dataset → take `ndp` through
  staging, then `analysis` (profile), then answer.
- Asks to PLOT / chart / visualize displacement → also spawn `visualization`.
- Asks for the full study ("resolve … find … stage … analyze … produce a PNG …
  explain") → run the whole pipeline (`geospatial` → `ndp` → `analysis` →
  `visualization`), then answer.

Prefer the smaller scope the user actually named; a later turn can always ask for
more. But do NOT stop SHORT of what was asked: if the request wants analysis or a
plot, a staged station CSV is the TRIGGER to continue (→ `analysis` →
`visualization`), not completion — "data acquisition complete" / "ready for
downstream" mean spawn onward, not answer yet. Even the honest no-coverage case
(a region with NO in-region station → `ndp` → answer) ends with YOU writing the
answer.

Start wherever the request calls for: usually `geospatial`, to turn a place name
into coordinates. But `geospatial` is just the place-name→coordinates resolver — if
the request ALREADY gives explicit coordinates (and a radius), it adds nothing, so
you may spawn `ndp` directly with those coordinates. Let what the request
contains decide; nothing forces a fixed first hop.
