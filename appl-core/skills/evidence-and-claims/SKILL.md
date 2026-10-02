---
name: evidence-and-claims
title: Evidence and Claims
description: Tag every claim about data as stated, checked, or inferred, give it a provenance line, keep a list of open questions for the data owners, and report uncertainty honestly. Use whenever you write an experiment card, a finding, or a report.
keywords:
- level:L0
- provenance
- uncertainty
---

# Evidence and claims

Every statement you make about a dataset carries one tag. The tag says how
the reader can check it.

| Tag | Meaning | Provenance line must name |
| --- | --- | --- |
| `[stated]` | The data's own documentation, manifest, or catalog says it | the file and section, or the manifest key |
| `[checked]` | You verified it in the data during this work | the command/script and the number it printed, or the card entry that recorded it |
| `[inferred]` | Your interpretation: plausible, not established by the files | the evidence it rests on, and who can confirm it |

Rules:

1. **Default to the weaker tag.** A column name is not documentation: a
   `_mm` suffix is `[stated]` only if a document defines it; that the values
   are millimetres is `[checked]` only after a plausibility check; that they
   are *correct* millimetres may still be `[inferred]`.
2. **`[stated]` is not `[checked]`.** Documentation can be wrong or stale.
   When a stated fact matters for a result (a unit, a count, a formula),
   check it and record both.
3. **Every `[inferred]` fact is also an open question** unless the user has
   confirmed it in this conversation (then record who confirmed it and
   re-tag it `[stated]` with the user as the source).
4. **Provenance lines are short and reproducible**: `(source: README,
   "Units" section)`, `(evidence: audit_columns.py on <table>, 12% empty)`,
   `(why: plateau coincides with bounding boxes at crop edge)`. Copy numbers
   from tool output; never round them into new facts.
5. **Numbers in answers come from the current tool output or the card**, with
   the tag of their source. If you did not compute it, do not state it.

## Open questions for data owners

Ask instead of guessing whenever the answer changes an analysis: what a
treatment or factor level means and its unit, whether a suspicious unit or
scale is real, whether zeros or blanks are real values, which of two
disagreeing sources is authoritative, what an undocumented flag means. Write
each as one question plus why it matters. In an interactive session, ask the
user (with `ask_user` when available) and continue with the conservative
choice meanwhile; in a child agent, only record the question.

## Reporting uncertainty

- Separate what is known from what is assumed in every answer: a short
  "Assumptions" or "Caveats" line is enough.
- State the scope of a check: sample vs full table, which tables, which
  period.
- Prefer ranges and counts with denominators ("in 412 of 2,000 sampled rows")
  over adjectives ("many").
- When evidence conflicts, show both sides and say which one the analysis
  used and why.
- A null result is a result: say what was checked and found clean.
