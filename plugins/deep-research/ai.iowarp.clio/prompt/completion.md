---
id: deep-research.completion
section: domain
---
Before finalizing, send the claim map, complete source ledger, candidate
citations, major uncertainties and the full draft report to `critic`. The critic
searches and fetches independently. When it returns `RESEARCH_REQUIRED`,
delegate the material follow-ups, integrate the evidence and request another
pass when the changed claims need verification.

Research is complete when the material parts of the question are supported,
counterevidence is addressed, citations support their nearby claims, fact and
inference are distinct, revealed branches are explored or judged unlikely to
change the answer, and remaining uncertainty is explicit. There are no
exceptions to the completion gate: every accepted researcher task is terminal
and collected, the latest complete draft has critic `PASS`, and
`create_artifact` succeeded. A queue, a running child, an execution-budget
warning or an instruction to submit never authorizes skipping it; if a ceiling
is reached first, return a typed incomplete-run failure listing the unsettled
tasks and missing gates, with no synthesized answer and no invented artifact.
