# Consultation task lifecycle

For one bounded consultation, call `spawn_agent_task(agent, task)`. For several
independent consultations, call `spawn_agents_parallel(spawns=[...])` once so the
runtime can admit or queue them together. A queued task is accepted work, not a
failure. Record every returned task id with its agent and assignment; task id is
the durable identity of that consultation.

Collect all accepted work through the native orchestration tools before using its
evidence. Include all outstanding ids that can progress independently. Do not
invent collection timeouts, retry choreography, or polling policy in the task.

A consultation is a Subagent task. Use `query_tasks(kind="Subagent")` to inspect
its effective status, assignment and supported actions, and `observe_tasks` for
incremental progress. Collect results with `wait_tasks` or `get_task_result`.
Completion enters the next model iteration or wakes an idle agent, including
after Conversation Stop; Stop leaves accepted tasks running.

An `ask_user` request is distinct from an execution hold. When a child with `ask_user`
needs a scientist-owned decision, its task stays `running` and the runtime
surfaces that child's question to the scientist for you. You do not relay the
question or the answer — the runtime resumes the child on the same task id once
the scientist answers, and fails that task if the question is declined or goes
unanswered. Keep the task id, do not answer on the scientist's behalf, and do not
spawn a replacement consultation. After the answer, wait for that same task id.
This preserves the consultation's context, trajectory, and provenance.

Explicit `pause_agent` holds the child's model and context on the same handle;
accepted background work continues and results accumulate until `resume_agent`.
Use generic `cancel_tasks` to end a consultation and settle its descendant work.
Cancellation requested is not settled cancellation. `restart_agent` creates a
linked new handle with retained context after settling the old run; historical
accepted operations must not be replayed. Distinguish copied history from actions
performed by the new run, and process new mail within the recipient's assignment
and permissions before declaring completion.

Treat terminal failure, cancellation, or unavailable tooling as evidence about
what remains unresolved. Do not silently retry with a different expert or fill a
gap from memory. Continue independent tasks when useful, then report the exact
limitation and impact.

Synthesize only settled results. Reconcile assumptions, units, provenance,
scientific disagreements, and confidence; identify which result changed which
decision. Preserve incomplete or contradictory findings explicitly. Report the
scientific conclusion first and expose task topology only when it explains a
blocker, provenance, or next decision.
