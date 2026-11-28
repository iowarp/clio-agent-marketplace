---
id: document-production.shell-conversions
section: domain
when: {"tools": ["shell_bash"]}
---
`shell_bash` with `background=true` runs a slow conversion as a Shell task
handle while other work continues; `observe_tasks` inspects it, `wait_tasks`
collects it and `cancel_tasks` cancels it. Acceptance is not a finished
artifact: the format and rendering are only checkable after the conversion
actually succeeds.
