# Craft: what makes a teardown read well

These rules are adapted from the community `teardown` skill by elvarofficial
(github.com/elvarofficial/teardown, MIT), whose review rules come from
whaleyxbt/claude-motion (MIT). They apply to the page and to Blender alike.

## Truth first

1. **Start from a reference, never imagination.** One source for the real thing: a
   manual, a patent, a datasheet, a measured teardown, a standard. The silhouette, the
   part count and the layout come from it.
2. **Real numbers from one source.** Take every size from the same source so they agree.
   Check one by hand (a gear pair's centre distance, a stroke, a bore) and say which.
   Write what you estimated into `source.estimated`.
3. **One input drives everything.** Every moving part is a function of the one `input`
   through a ratio, a phase or a table. Nothing is keyed by hand, so the motion is right
   at every input value.

## Show the mechanism

4. **The part doing the work opens up.** The housing gets `cutaway`, the step that
   explains it turns on `section` or isolates it with `focus`, and the part itself
   carries the `accent`.
5. **Stages read like a real strip-down.** Covers and their fasteners first (order 0),
   then what they held, then the core. Fasteners travel a little further than the part
   they hold, along the same direction.
6. **Fix collisions with a number, never with the camera.** When `check` lists an
   overlap, change a distance, a direction or a stage. Never hide a part or pick a view
   that hides the clash.
7. **Pick the camera for the mechanism.** A three-quarter view for most things; never
   face-on for a planar linkage, where every part sits behind the next. Set it in
   `camera`, and per step with `view`.

## Look

8. **A studio, one accent.** Neutral background, soft light, real materials. The accent
   means something: the input, the output or the part being explained, never decoration.
9. **Large metal stays matte.** Use `cast-iron`, `aluminium` or `painted` for large
   bodies; keep `chrome` and `gold` for small parts so nothing blows out to white.
10. **Near-white parts need edges.** Turn on edges (`#edges=1`) or pick a darker colour
    when a white plastic part disappears into the background.
11. **The machine fills 60 to 70 percent of the frame**, with nothing closer than about
    60 px to an edge.
12. **Keep the page under 1 MB.** Lower `segments` on big curved parts, use `repeat`
    rather than copies, and simplify STL parts.

## Review loop

Never report a teardown done without reading screenshots of the current build. Look at
assembled, fully exploded with labels, every step, the section and a mid-cycle input,
and check:

- **Mechanism.** Parts that should touch do (gear teeth mesh, a shaft sits in its bore,
  a bolt sits in its hole); nothing passes through anything at any input value.
- **Composition.** One focal point per step; labels do not cover their own parts; the
  assembly is not cut off at any explode amount.
- **Type.** No label, title or step text is clipped.
- **Truth.** It still looks like the reference: proportions, part count, layout.
- **Timing.** One play cycle (`input.seconds`) is slow enough to follow.

Fix, rebuild, look again. Stop only when a full pass finds nothing.
