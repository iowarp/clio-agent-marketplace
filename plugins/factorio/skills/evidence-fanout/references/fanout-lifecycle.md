# Evidence fan-out lifecycle

An evidence question comes with the decision it informs, its scope, time
horizon, source families, terminology already known, and exclusions. Lanes
are parts that can be investigated independently without duplicating the
whole question: mechanisms, measurements, material/condition regimes,
competing methods, standards, datasets, or counterevidence, chosen from the
question rather than a fixed template.

Independent `evidence_leaf` assignments start together with
`spawn_agents_parallel`; each returned task handle collects with `wait_tasks`.
`observe_tasks` shows progress while independent work continues; completion
arrives at the next model iteration or wakes an idle coordinator. Evidence is
mature only when all settled packets say so. New terminology, cited primary
work, contradictions, missing conditions, or method branches matter when they
could change the scientific decision; a follow-up may be one leaf or another
independent fan-out.

A coherent claim map and source audit go to one `evidence_critic` with the
entire draft, citations, uncertainties, and audit; the critic makes fresh web
checks. `RESEARCH_REQUIRED` names material gaps, and a revised complete
packet goes to another independent review. Extra rounds after `PASS` add
nothing, and an incomplete critic result is not approval.

When a child asks the scientist with `ask_user`, the runtime resumes that same
task after the answer, under its original task id. A lane that fails
terminally leaves an evidence gap; its impact belongs in the critic packet and
final result, and independent lanes can continue.
