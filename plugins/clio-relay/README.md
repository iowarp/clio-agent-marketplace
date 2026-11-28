# Relay's CLIO plugin

This folder is relay's plugin for CLIO. Installing it gives CLIO:

- relay's MCP server, launched from `mcp.json`, with the five verbs
  `describe`, `run`, `exec`, `files` and `serve`, and beside them `install`,
  the read tools `exec_read`, `files_read` and `packages_read`, `packages`,
  `cancel`, `site_clean` and `shutdown` (see relay's
  [architecture](https://github.com/iowarp/clio-relay/blob/jaimecernuda-relay-rework/docs/architecture.md));
- the Compute page in CLIO's left bar, where a person adds, probes, edits and
  removes compute endpoints (relay's sites) and picks each one's protocol,
  security and spending;
- a Globus account, whose grant file CLIO hands relay as
  `CLIO_RELAY_GRANT_FILE_GLOBUS`;
- sign-in pages on the loopback address and on `https://tacc.tapis.io`;
- the `use-relay` skill, which sends the agent to relay's skill resources.

`ai.iowarp.clio/a2ui/clio-relay-compute/` is the A2UI catalog the page draws
with: ten Basic components, unchanged, and CLIO's choice table. A client
that renders only the Basic catalog gets the page as cards.

CLIO's fence lets a plugin server write only to its own data folder, so
`mcp.json` puts relay's configuration (`sites.yaml`, skills) and state in
`${PLUGIN_DATA}/config` and `${PLUGIN_DATA}/state`. To use the same sites from
a terminal, point `CLIO_RELAY_CONFIG_DIR` and `CLIO_RELAY_STATE_DIR` at those
folders.

`mcp.json` runs relay with `uv run --project ${PLUGIN_ROOT}/server --frozen
--no-dev` from `server/`, a hash-locked project whose one dependency is a released
clio-relay wheel. The published copy lives in the CLIO agent marketplace as
`plugins/clio-relay/`; when relay changes, cut a release, point
`server/pyproject.toml` at its wheel and run `uv lock --project server`.

The plugin carries no packages. Each site has one JARVIS root of relay's,
which relay sets up with jarvis-cd and clio-jarvis at the commits the relay
release pins, and `run` takes the packages that root holds. A person's own
package reaches a site with `files` and joins the root through `packages`
(see relay's
[operations](https://github.com/iowarp/clio-relay/blob/relay_ready/docs/operations.md#the-sites-jarvis-root-and-its-packages)).
