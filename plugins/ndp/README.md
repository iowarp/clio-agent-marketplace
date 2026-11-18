# ndp

The National Data Platform (NDP) package. Add it to any agent (the `ndp`
agent is the standard agent plus this plugin) to work with NDP:

- **Built-in NDP tools** (claimed in `ai.iowarp.clio/tools/builtin.py`):
  organization lookup and dataset search are available in any workspace,
  with no attached dataset, saved Endpoint or sign-in; search filters by
  resource format and returns each resource's own description. Endpoint
  connection, operations, requests and artifact upload are deferred and load
  on demand. Attaching and reading data uses the `connected-data` plugin,
  which this plugin requires.
- **`work-with-ndp`** ("Working with NDP"): the skill to load for any NDP
  work. It explains NDP's concepts (organizations, datasets, resources,
  catalogs, Endpoints), the discovery -> attach -> analyze path, Endpoint
  operations and publishing, with references and offline helper scripts.

Organization-specific conventions (for example which datasets are
EarthScope's and how its stations are named) belong in that organization's
own package that requires this one, such as `earthscope`.
