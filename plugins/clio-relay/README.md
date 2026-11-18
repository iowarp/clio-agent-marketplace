# Relay's CLIO plugin

This folder is relay's plugin for CLIO. Installing it gives CLIO:

- relay's MCP server, launched from `mcp.json`, with the five tools `describe`,
  `run`, `exec`, `files` and `serve`;
- the Compute tab, where a person adds, probes, edits and removes sites;
- a Globus account, whose grant file CLIO hands relay as
  `CLIO_RELAY_GRANT_FILE_GLOBUS`;
- sign-in pages on the loopback address and on `https://tacc.tapis.io`;
- the `use-relay` skill, which sends the agent to relay's skill resources.

`ai.iowarp.clio/a2ui/clio-relay-compute/` is the A2UI catalog the tab draws
with. It is ten Basic components, unchanged, so CLIO renders everything the
tab sends.

`mcp.json` runs relay with `uvx` from a pinned commit of
[clio-relay](https://github.com/iowarp/clio-relay). This folder is a copy of
that repository's `plugin/` folder at the pinned commit; when relay changes,
copy the folder again and move the pin.
