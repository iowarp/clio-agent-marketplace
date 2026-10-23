---
id: workspace.edits
section: capabilities
when: {"tools": ["fs_write_file", "fs_edit_file"]}
---
`fs_write_file` creates a file or replaces its whole content; `fs_edit_file`
replaces an exact string in an existing file (`old_string` must occur once
unless `replace_all` is set). Both change the file on disk when they return.
The session's permission mode decides whether the person is asked first, and a
refused write comes back with its reason. Each result carries the diff of the
change, and the person sees every change in the diff panel, where they can undo it.
