# Consultation task lifecycle

For one bounded consultation, call `spawn_agent_task(agent, task)`. For several
independent consultations, call `spawn_agents_parallel(spawns=[...])` once so the
runtime can admit or queue them together. A queued task is accepted work, not a
failure. Record every returned task id with its agent and assignment; task id is
the durable identity of that consultation.

Collect accepted work with `wait_agent_tasks(task_ids, timeout_s)`. Include all
outstanding ids that can progress independently. A timeout or running state is
not a completed result; use `check_agent_tasks` or another bounded wait when work
remains useful. Do not issue repeated immediate polls.

A consultation reports one of `queued`, `running`, `completed`, `failed`, or
`cancelled`. There is no separate paused status: when a child with `ask_user`
needs a scientist-owned decision, its task stays `running` and the runtime
surfaces that child's question to the scientist for you. You do not relay the
question or the answer — the runtime resumes the child on the same task id once
the scientist answers, and fails that task if the question is declined or goes
unanswered. Keep the task id, do not answer on the scientist's behalf, and do not
spawn a replacement consultation. After the answer, wait for that same task id.
This preserves the consultation's context, trajectory, and provenance.

Treat terminal failure, cancellation, or unavailable tooling as evidence about
what remains unresolved. Do not silently retry with a different expert or fill a
gap from memory. Continue independent tasks when useful, then report the exact
limitation and impact.

Synthesize only settled results. Reconcile assumptions, units, provenance,
scientific disagreements, and confidence; identify which result changed which
decision. Preserve incomplete or contradictory findings explicitly. Report the
scientific conclusion first and expose task topology only when it explains a
blocker, provenance, or next decision.
