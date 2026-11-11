CLIO Marketplace 0.8.0-beta.1 ships the default agents and plugins for CLIO
0.9.6-beta.1. It adds National Data Platform work without an MCP server, paper
writing with venue templates, an in-app browser and notebook pairing.

### Work with the National Data Platform

The new NDP agent is the standard agent plus the NDP plugin, which uses CLIO's
built-in tools to look up organizations and search datasets. EarthScope builds on
it and names EarthScope's station catalog, per-station position series and
services. The standard agent no longer searches NDP itself; use the NDP agent or
add the NDP plugin. (#127)

### Write and check scientific papers

LaTeX papers build through CLIO, which reports each problem by file and line and
checks the paper against its venue (page limit, double-blind review, required
packages, paper size). Six templates cover IEEE, ACM, Springer LNCS and Elsevier
venues. A comment on the built PDF leads back to its source line and, for a
registered figure, to the script that drew it. The WTF-P plugin adds a method for writing a paper from
evidence; add it to an agent to use it. (#120, #123)

### Drive a browser and pair on notebooks

The standard agent can drive CLIO's in-app browser from code. Only the person can
trust a certificate, and a refused page is reported rather than opened. The marimo
plugin pairs with the person on a running notebook; add it to the agents that
should use it. (#119, #122)

### Review a working session

SPOTTER reads a session as a careful colleague would. Only the person's own
messages state their intent; an instruction found inside a tool result, file or
fetched page is treated as evidence. A warning informs the person, a danger
finding quarantines the session, and every concluded finding becomes a card. (#124)

## Changed

Delegation roles use shorter prompts, and skills carry one-sentence descriptions.
Small studies run inside the conversation, and dashboards read the latest version
of their file and stream sources. (#122)

## Fixed

The HDF5 guides correct the `h5format_convert` usage, a missing import and a
reference to a removed guide. (#118)

See the
[CHANGELOG](https://github.com/iowarp/clio-agent-marketplace/blob/v0.8.0-beta.1/CHANGELOG.md)
for the complete changes.
