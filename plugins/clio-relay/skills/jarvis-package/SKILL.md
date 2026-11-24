---
name: jarvis-package
title: Writing a JARVIS package for relay
description: Use this skill to write a new JARVIS package that relay can stage, install and run on the person's compute sites, for an application relay's package sources hold no package for (check packages_read's available first). The package is generic and takes the application's own input; the person's case is that input, not a package. It says where the bundled examples are, how the package folder is laid out, what its contract must hold and how to check it before staging.
---

# Writing a JARVIS package for relay

First make sure one is needed: `packages_read(match="<application>")` lists
under `available` every package relay's sources hold. When one is there for
the application, use it and write the person's case as its input instead
(see `use-relay`). When none is, write one package for the application, not
for the case: it takes the application's own input (a script, a namelist, a
settings file, or several files as one input bundle) as a parameter, and the
case reaches it as that input. A package built around one case (an obstacle
flow, one protein) cannot run the next case and is the wrong shape.

Relay runs a program on a site as a JARVIS package with a contract: `pkg.py`
(the JARVIS class), `contract.yaml` (what relay reads before it runs anything),
and the providers `progress.py` and `artifacts.py`. This plugin ships
clio-jarvis, whose packages are the models to copy, so writing a package needs
no other plugin, connector or download. The separate Jarvis connector drives a
JARVIS-CD of its own and is not needed to write, stage or run a package
through relay; do not offer it for this.

## Find the bundled clio-jarvis

`packages_read` lists relay's package sources under `sources`. The folder
`<source>/clio-jarvis` is clio-jarvis at the pin this plugin bundles, and
`<source>/jarvis-cd/builtin` is jarvis-cd's builtin repository at relay's
JARVIS pin (packages without contracts, useful for how a `pkg.py` installs
and launches an application). The clio-jarvis layout:

- `clio_jarvis/clio_jarvis/_contract/`: the shared code every package uses
  (`base.py` with `ClioApplication` and `ClioService`, `spec.py` with
  `load_contract`, `runtime.py` with the provider adapters).
- `clio_jarvis/clio_jarvis/<package>/`: the shipped packages. Read the one
  nearest to the new program before writing: `gray_scott` (a short MPI
  solver with a growing BP5 output), `xcompact3d` (an input file, a geometry
  and a long case), `wrf` (a case fetched on the site, one netCDF file per
  step, a Spack builtin recipe) and `pvserver` (a service).
- `schemas/package-contract.v1.json`: the contract's schema. Check a part
  you are unsure of here rather than guessing.
- `spack/`: clio-jarvis's own Spack recipes, for software Spack's builtin
  repository lacks.

Read these files where they are; do not fetch clio-jarvis from GitHub.

## Lay the package out

Write it in the person's workspace as a JARVIS repository of its own, named
for the work (`md_pkgs`, say), beside its `schemas/`:

```
<workspace>/<repo>/            the folder you give packages(op="stage", dir=...)
  schemas/                     a copy of the bundled schemas/
  spack/                       only when the package brings its own recipes
  pyproject.toml               only when pkg.py needs Python packages on the site
  <repo>/                      the JARVIS repository
    <repo>/
      __init__.py
      _contract/               a copy of the bundled _contract/, unchanged
      <package>/
        pkg.py  contract.yaml  progress.py  artifacts.py  [selftest.py]
```

`_contract` finds `schemas/` three levels up, so keep this shape and do not
edit `_contract`. In the copied `progress.py`, `artifacts.py` and `pkg.py`,
change the imports from `clio_jarvis.` to `<repo>.`. The package's name for
`run` is `<repo>.<package>`.

## Write pkg.py and contract.yaml

- `pkg.py` subclasses `ClioApplication` (or `ClioService` for a service) and
  returns its parameters from `_configure_menu` as one literal list of literal
  dicts, each with `name`, `msg` and `type`. Keep `nprocs`, `ppn`,
  `cores_per_node`, `walltime` and `queue` as the shipped packages have them.
- Take the application's input as a parameter naming a file (`script`, say,
  or `input` for a bundle unpacked into the run directory). A run sets it to
  the name of a job input, and relay puts that file in place (see `use-relay`).
  Keep every case-specific value in that input, not in `pkg.py` or the contract.
- The contract needs every part: `install`, `parameters`, `resources`,
  `sizing`, `outputs`, `progress`, `provenance` and `selftest`, plus
  `service` for a service. A missing part refuses the package and names it.
- `install` is a Spack spec. Depend on the `mpi` virtual and never pin an MPI,
  so the site's MPI is reused. Use Spack's builtin recipe when it has one, as
  `wrf` does, so software the site already built is found.
- A value is a literal, `{param: name}` or two-operand arithmetic, `div`,
  `mul`, `add` or `ceil_div`, whose operands are numbers, parameter names or
  more arithmetic: frames that include the first are
  `{add: [{div: [nsteps, nstout]}, 1]}`.
- A snapshots output is what the viewer follows: give its `reader`,
  `expected_steps`, `follow` and `display`, and write each step whole, then go
  straight on. The run never waits for a viewer (see `use-relay`).
- `progress.step_pattern` matches the program's own step line and has a
  named group `step`; `done_pattern` matches its last line.
- Give the package a `version` and raise it with every change: the archive's
  SHA-256 changes, and the person reviews the new one.

## Check it, then stage it

Check the package statically on this machine: load it with
`<repo>._contract.spec.load_contract(<package dir>)`, which raises naming the
part at fault, and print its `describe()`. Do not run the program, the
package's self-test or unit tests here; the program belongs on the site. Then
stage it with `packages(op="stage", package="<repo>.<package>",
dir="<workspace>/<repo>")` and go on as `use-relay` says: install, then run.
The site checks the configuration again before any job starts and returns
its issues typed, so fix what it names and stage again.
