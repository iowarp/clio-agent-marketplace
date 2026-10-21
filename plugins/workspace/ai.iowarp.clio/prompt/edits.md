---
id: workspace.edits
section: capabilities
when: {"tools": ["fs_propose_edit"]}
---
Respect the session's execution and confirmation policies: propose edits with
`fs_propose_edit` when review is required, apply them only through
`fs_apply_edit_write`, and verify the result.
