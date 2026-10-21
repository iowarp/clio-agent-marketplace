---
id: appl-core.first-contact
section: domain
---
First contact with an export:

1. Locate the bundle supplied by the user or session. Treat it as read-only
   input even when a development copy allows writes; never repair, normalize or
   edit source files to make an analysis or bundled script succeed.
2. Use `appl-core-exports` to inspect the self-description and actual files. An
   unfamiliar or missing version, inconsistent manifest or absent expected
   column calls for investigation and adaptation, not blanket refusal.
3. Inspect the data relevant to the question, using `onboard-dataset` for
   useful checks. Choose direct queries, task-specific code and derived
   representations from what is present; no fixed five-table schema,
   `loader.py`, prepared card or repeat execution is required before answering.
4. Reuse a card or other saved evidence when relevant, rechecking the source
   files, assumptions and results the answer depends on; a manifest hash alone
   does not prove unchanged inputs. The optional card helper uses
   `CLIO_AGENT_WORKSPACE_STATE_DIR`; one conventional record is
   `<workspace_state>/datasets/<key>/experiment-card.md`.
5. Delegate an independent audit with `audit-dataset` when useful. Inspect its
   evidence and result before using it, repeating selected calculations when
   warranted. A child ending does not establish scientific success, and a
   mandatory second execution of its whole pipeline is not required.
