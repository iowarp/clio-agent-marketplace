---
id: document-production.conversions
section: domain
when: {"tools": ["shell_bash"]}
---
For a slow conversion, run `shell_bash` with `background=true` to get a Shell
task handle and continue independent work; inspect it with `observe_tasks`,
collect it with `wait_tasks`, or cancel it with `cancel_tasks`. Acceptance is
not a finished artifact: validate the format and review the rendering after the
conversion actually succeeds.
