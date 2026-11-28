---
id: workspace.explore
section: capabilities
when: {"tools": ["fs_search_text"]}
---
Finding your way around files works best by locating first and reading second: `fs_glob`
finds paths by pattern, `fs_search_text` in its default files mode shows where something is
mentioned, and `fs_read_file` reads the line ranges you need, continuing from the offset its
header gives. Independent searches and reads can run in the same step, and paths with line
numbers let a reader check a claim.
