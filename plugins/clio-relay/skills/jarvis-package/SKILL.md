---
name: jarvis-package
title: Writing a JARVIS package for relay
description: Use this skill to write a new JARVIS package that relay can install and run on the person's compute sites, for an application the site's JARVIS root holds no package for (check packages_read first). The package is generic and takes the application's own input; the person's case is that input, not a package. It says where the clio-jarvis examples are, how the repository is laid out, what its contract must hold, how to check it and how it reaches a site.
---

# Writing a JARVIS package for relay

`packages_read(site=..., match="<application>")` lists the packages the
site's JARVIS root holds; a package already there for the application takes
the person's case as its input (see `use-relay`). A package is for the
application, not the case: it takes the application's own input (a script, a
namelist, a settings file, or several files as one input bundle) as a
parameter, and the case reaches it as that input. A package built around one
case (an obstacle flow, one protein) cannot run the next case.

Relay runs a program on a site as a plain JARVIS package with a contract:
`pkg.py` (the JARVIS class), `contract.yaml` (what relay reads before it runs
anything), and the providers `progress.py` and `artifacts.py`. clio-jarvis's
packages are the models to copy. The separate Jarvis connector drives a
JARVIS-CD of its own and is not needed to write, add or run a package through
relay.

## Read clio-jarvis

clio-jarvis is in every site root relay set up, at the commit relay pins:
`packages_read` gives each `clio_jarvis.*` package's `repo_dir`, and
`files(op="read")` reads it there. It is also public at
`https://github.com/iowarp/clio-jarvis`. Its repository directory holds:

- `clio_jarvis/_contract/`: the shared helpers the packages import
  (`spec.py` with `load_contract`, `runtime.py` with the provider adapters,
  `files.py`, `flushwrap.py`, `fetch.py`). They are ordinary repository code,
  loaded the way JARVIS loads any repository.
- `clio_jarvis/<package>/`: the packages. The one nearest to the new program
  is the closest model: `gray_scott` (a short MPI solver with a growing BP5
  output), `wrf` (a case fetched on the site, one netCDF file per step, a
  Spack builtin recipe), `warpx` (a native inputs file, one AMReX plotfile
  per interval, a Spack recipe subclassed to fix one fault), `lammps` (a
  native input script, one particle frame per dump interval), `gromacs`
  (GROMACS's own case files, the gmx stages before the watched run, one frame
  per output interval) and `pvserver` (a service).
- `clio_jarvis/_spack/`: clio-jarvis's Spack recipes, only for what upstream
  Spack lacks or builds wrongly.
- `schemas/package-contract.v1.json`: the contract's schema, which settles
  any part of the contract.

## The repository's layout

The package lives in the person's workspace as a JARVIS repository of its
own, named for the work (`md_pkgs`, say). The outer directory and the package directory
inside it carry the same name:

```
<repo>/                        the directory you copy to the site and add
  schemas/                     a copy of clio-jarvis's schemas/
  <repo>/
    __init__.py
    __main__.py                a copy of clio-jarvis's, for validate
    _contract/                 a copy of clio-jarvis's _contract/, unchanged
    _spack/                    only when a package brings its own recipes
    <package>/
      pkg.py  contract.yaml  progress.py  artifacts.py  [selftest.py]
```

`_contract` finds `schemas/` two levels above itself, so it works only in
this shape and as an unchanged copy. The copied `pkg.py`, `progress.py` and
`artifacts.py` import from `<repo>.` instead of `clio_jarvis.`. The
package's name for `run` is `<repo>.<package>`. Nothing in the repository
imports, subclasses or calls a jarvis-cd `builtin` package or clio-jarvis:
a site relay set up has no `builtin` repository, and the copy of `_contract`
makes the repository stand alone.

## Write pkg.py and contract.yaml

- `pkg.py` subclasses JARVIS's own `jarvis_cd.core.pkg.Application` (or
  `Service` for a service) and returns its parameters from `_configure_menu`
  as one literal list of literal dicts, each with `name`, `msg` and `type`.
  JARVIS lists that menu without importing the package, so it has to be
  literal. Relay sets `nprocs`, `ppn`, `cores_per_node`, `walltime` and
  `queue` as the clio-jarvis packages have them, and JARVIS calls `start`,
  `stop` and `clean`. An
  optional `check_config(self, config)` raises on a configuration the
  program would reject, before any job starts.
- Take the application's input as a parameter naming a file (`script`, say,
  or `input` for a bundle unpacked into the run directory). A run sets it to
  the name of a job input, and relay puts that file in place (see `use-relay`).
  Keep every case-specific value in that input, not in `pkg.py` or the contract.
- One run is one piece of work. When the person's work has parts that do not
  depend on each other (independent stages, cases or ensemble members), each
  is its own run of the package with its own input, not a loop inside one:
  run in series in one job they take the sum of their times on the same
  nodes, and as separate runs they can go side by side (see `use-relay`'s
  layout section). A part that needs another's output is a later run that
  takes it as its input.
- Expose the application's own parallel-decomposition controls as
  parameters. Many MPI codes split the work further than the rank count,
  through options of their own: groups of ranks that each take part of the
  problem, a process grid, a domain split, task or band groups. Read the
  application's parallel documentation for every such control it has, and
  make each one a parameter, passed where the application reads it (its
  command line, usually). Default each to the application's own default, so
  leaving it unset runs as the program would, and say in `msg` what it
  splits and what it must divide. A package with only the input and the rank
  count leaves the person no way to tune a run, and a pilot can't compare
  decompositions, or size a run to the partition's nodes (see `use-relay`'s
  layout section). A control that lives inside the application's input file
  stays in that input. Leave threads per rank alone: JARVIS sets them from
  each rank's share of the allocation.
- The contract needs every part: `parameters`, `resources`, `sizing`,
  `outputs`, `progress`, `provenance` and `selftest`, plus `service` for a
  service. A missing part refuses the package and names it. `title` is
  optional. The install is not a contract part: it lives in the menu (below).
- Write `sizing` so an agent can size a run against a partition: `ranks`
  names the problem's own parallel units (k-points, pools, images, domains,
  the process grid) and how the rank count and each decomposition control
  should relate to them, the fewest ranks whose share fits in memory and the
  most that still do useful work, each as a rule over the problem's units,
  not a number; `nodes` follows from ranks and the partition's physical cores
  per node. Say there how pilots at sizes chosen from those bounds and the
  queue's idle nodes show where adding nodes stops paying. Write no node or
  rank count as a default or an example: the case's numbers live in its
  input, and the machine's in `describe`.
- The menu's `install_method`, `install_query` and `install_repos` say how
  JARVIS installs the software. `spack`, the method for every application,
  takes a Spack spec as `install_query`. A spec on the `mpi` virtual, with no
  MPI pinned, reuses the site's MPI. Upstream Spack's recipe, when it has
  one, finds software the site already built, as `wrf` does. A recipe that
  fails for the variants needed can be subclassed in the repository's
  `_spack/` with only the fault fixed, as clio-jarvis's `warpx` recipe does,
  and listed in `install_repos` (relative to the package directory,
  `["../_spack"]`). A recipe that patches the application for relay's tooling
  builds something other than the application. A Spack recipe is not a
  JARVIS package, so this is no `builtin` dependency.
- `pip`, `conda` or `container` is only for software with no MPI and nothing
  compiled against the site, such as a Python-only analysis tool. The
  contract refuses an MPI (or an MPI decomposition) installed with pip or
  conda: an MPI code is a Spack package, whatever else it offers.
- Site facts come from JARVIS and the resource graph, not from `pkg.py`:
  JARVIS's own `Exec(command, MpiExecInfo(nprocs=..., ppn=...,
  hostfile=self.hostfile, env=self.mod_env, ...)).run()` launches the
  program, as in `gray_scott`, and `shared_dir` and `private_dir` are where it
  writes. JARVIS launches on the package's own hosts inside the job, and
  refuses a layout that does not fit them rather than changing it. An
  `mpirun` line, module, launcher flag, node name or site path in the package
  ties it to one site. jarvis-cd's own `builtin` packages hardcode these; one
  in jarvis-cd's repository (`builtin/` in grc-iit/jarvis-cd) still shows how
  an application installs and launches.
- A value is a literal, `{param: name}` or two-operand arithmetic, `div`,
  `mul`, `add` or `ceil_div`, whose operands are numbers, parameter names or
  more arithmetic: frames that include the first are
  `{add: [{div: [nsteps, nstout]}, 1]}`.
- A snapshots output is what the viewer follows: give its `reader`,
  `expected_steps`, `follow` and `display`, and write each step whole, then go
  straight on. The run never waits for a viewer (see `use-relay`).
- `progress.step_pattern` matches the program's own step line and has a
  named group `step`; `done_pattern` matches its last line. Give `total`, the
  steps a run takes, as a value over its parameters; for work that stops on
  its own (a relaxation that converges, an adaptive solver), the most it
  allows. JARVIS records when each step was seen, and relay turns that into
  the run's pace and its projected end beside the time limit, which is how
  anyone watching learns early that a run will not finish in time. Pick the
  line the program prints for each unit of its work, so the pace measures
  that work.
- Give the package a `version` and raise it with every change. The review
  identity is the digest of the package directory and the repository's `_*`
  files as they sit on the site, so any edit is reviewed again.

## Checking it and adding it

`python -m <repo> validate <package>`, from the outer `<repo>/` directory,
checks the package statically on this machine and names the part at fault;
`python -m <repo> describe <package>` prints what relay reads. The program,
its self-test and its unit tests need the site's software, so they run on the
site.

The outer `<repo>/` directory reaches the site with `files`, into the
person's space there, and `packages(op="add", site=..., path="<that directory
on the site>")` registers it in the site's root; relay lists the site's
packages again, and `force: true` replaces an earlier copy of that
repository. The site checks the configuration again before any job starts and
returns its issues typed, naming what to change; an edited copy goes up with
`files` the same way.