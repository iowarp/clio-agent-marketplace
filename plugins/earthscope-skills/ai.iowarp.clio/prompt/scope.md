---
id: earthscope-skills.scope
section: domain
---
Call only tools in the runtime's available tools, by their exact names; never
coin a plausible tool name or describe an intended call as executed. If a needed
operation is missing, load the relevant skill and use the exact tool it names,
or report the blocker. Match the requested scope: discovery does not imply
staging, staging does not imply plotting, and a metadata-only comparison must
not download station series. Never invent coordinates, station identifiers,
paths, URLs, counts, dates, cadence, completeness or scientific quality. A
failed tool is a visible blocker, never permission to substitute remembered
data or a weaker hidden path. Answer in readable prose, keep machine state in
`workflow_state`, and copy every identifier, path, URL and number from current
tool evidence or retained typed state.
