"""jarvis-cd base classes for clio-jarvis packages.

A package subclasses :class:`ClioApplication` or :class:`ClioService`, defines
``_configure_menu`` and ``start``, and may override ``_clio_prepare`` to write
its input files. The mixin does the RL40 parts that are the same everywhere:
resolve and check the parameters against ``contract.yaml``, fill the empty
ones, write ``clio-contract.json`` into the package's shared directory, and
describe the runtime to jarvis-cd's deployment contract.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from jarvis_cd.core.pkg import Application, Service
from jarvis_cd.deployment import (
    ConfigurationCondition,
    ExecutionProfile,
    PackageDeploymentContract,
    ReadinessContract,
    RuntimeRequirement,
    RuntimeStatus,
    probe_program,
)
from jarvis_cd.shell import Exec, MpiExecInfo

from .spec import RESOLVED_SCHEMA, Contract, in_job, job_cores_per_node, load_contract, physical_cores

#: Parameters the fill rule set on the last configure, so a re-configure refills them.
FILLED_KEY = "_clio_filled"
RECORD_NAME = "clio-contract.json"

# OpenMPI's mpiexec gets every variable as -x KEY="VALUE"; these would break that line.
_UNSAFE_ENV_VALUE = re.compile(r'["$`\\\n]')


def mpi_safe_env(env: Mapping[str, Any]) -> dict[str, str]:
    """The environment without exported shell functions or values mpiexec cannot quote."""
    return {
        key: str(value)
        for key, value in env.items()
        if isinstance(value, (str, int, float))
        and not key.startswith("BASH_FUNC_")
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
        and not _UNSAFE_ENV_VALUE.search(str(value))
    }


class _ClioPackage:
    """Shared RL40 behaviour. Mixed in ahead of a jarvis-cd base class."""

    #: Program the package's install puts on PATH; the deployment contract probes it.
    clio_program: str = ""
    #: None: check the program is on PATH without running it.
    clio_probe_arguments: tuple[str, ...] | None = ("--version",)
    clio_probe_return_codes: tuple[int, ...] = (0,)
    clio_capabilities: tuple[str, ...] = ()

    _clio_contract_cache: Contract | None = None

    # -- contract -----------------------------------------------------------

    def clio_contract(self) -> Contract:
        if self._clio_contract_cache is None:
            self._clio_contract_cache = load_contract(Path(self.pkg_dir))
        return self._clio_contract_cache

    #: Install menu keys the contract fills, with the entry to add when jarvis-cd's menu lacks one.
    _CLIO_INSTALL_ENTRIES: dict[str, dict[str, Any]] = {
        "install_repos": {
            "msg": "Spack repositories with recipes the install_query needs beyond Spack's builtin",
            "type": list,
            "args": [{"name": "repo", "msg": "Spack repository directory, relative to the package directory", "type": str}],
        },
        "install_channels": {
            "msg": "Conda channels the install_query comes from, in order",
            "type": list,
            "args": [{"name": "channel", "msg": "Conda channel", "type": str}],
        },
        "install_methods": {
            "msg": "Ways to install the package; JARVIS uses the one this site fits and asks when several fit",
            "type": list,
        },
    }

    def configure_menu(self) -> list[dict[str, Any]]:
        """jarvis-cd's menu with the contract's install part as the install defaults.

        ``jarvis ppl install`` hands each package to the installer for its
        method, which reuses what the site already has and installs the rest.
        Spack repositories are relative to the package directory and jarvis-cd
        resolves them on the host that loads the package, the site that runs
        the job.
        """
        install = self.clio_contract().install()
        menu = [dict(entry) for entry in super().configure_menu()]  # type: ignore[misc]
        for entry in menu:
            if entry.get("name") in install:
                entry["default"] = install[entry["name"]]
        present = {entry.get("name") for entry in menu}
        for name, entry in self._CLIO_INSTALL_ENTRIES.items():
            if name in install and name not in present:
                menu.append({"name": name, **entry, "default": install[name]})
        return menu

    def _clio_placement(self) -> dict[str, Any]:
        return {
            "shared_dir": str(self.shared_dir),
            "private_dir": str(self.private_dir),
            "pkg_dir": str(self.pkg_dir),
        }

    def _clio_runs_here(self) -> bool:
        """True when the ranks run on this host only (no hostfile, or a local one)."""
        hostfile = self.hostfile
        return hostfile is None or not len(hostfile) or hostfile.is_local()

    def clio_ppn(self) -> int | None:
        """Ranks per node for the launch, decided on the host that launches them.

        ``ppn``, else ``cores_per_node`` (the target partition's physical cores,
        both filled at configure), else the physical cores of the job's node
        when this runs inside a batch allocation, else this host's when the
        ranks run here. Otherwise None, which leaves placement to mpiexec: the
        configuring host, often a login node, is never asked. This is a default
        passed with ``nprocs``: inside an allocation JARVIS's MPI exec bounds it
        by the scheduler's task geometry and records the decision as
        ``placement`` in the launch record.
        """
        sizing = self.clio_contract().data["sizing"]["processes_per_node"]
        for name in (sizing["param"], sizing["cores"]):
            value = self.config.get(name)
            if value not in (None, ""):
                return int(value)
        cores = job_cores_per_node()
        if cores is None and not in_job() and self._clio_runs_here():
            cores = physical_cores()
        return cores

    def _configure(self, **kwargs: Any) -> None:
        super()._configure(**kwargs)  # type: ignore[misc]
        resolved = self._clio_resolve(kwargs)
        self._clio_prepare(resolved)
        self._clio_write_record(self.clio_contract(), resolved)

    def check_config(self, config: dict[str, Any]) -> None:
        """The contract's defaults, fills and parameter schema, as configure applies them.

        JARVIS calls this on the submitting host before a plan or submit, so a
        value configure would refuse in the job is refused before any job starts.
        """
        contract = self.clio_contract()
        names = {entry["name"] for entry in contract.menu}
        given = {name: config[name] for name in names if name in config}
        contract.check_parameters(contract.resolve_config(given, self._clio_placement()))

    def _clio_resolve(self, kwargs: Mapping[str, Any]) -> dict[str, Any]:
        """Apply the contract's defaults and fill rules to ``self.config`` and check it."""
        contract = self.clio_contract()
        names = {entry["name"] for entry in contract.menu}

        # A value the fill rule chose last time is not a user choice: refill it.
        previous = self.config.get(FILLED_KEY) or {}
        for name, value in previous.items():
            if name not in kwargs or kwargs[name] == value:
                self.config[name] = ""

        given = {name: self.config.get(name) for name in names if name in self.config}
        resolved = contract.resolve_config(given, self._clio_placement())
        contract.check_parameters(resolved)
        self.config.update(resolved)
        self.config[FILLED_KEY] = {
            name: resolved[name]
            for name in names
            if given.get(name) in (None, "") and resolved.get(name) not in (None, "")
        }
        return resolved

    def _clio_ensure_configured(self, *, prepare: bool) -> None:
        """Resolve the contract when this package was never configured.

        ``jarvis ppl start`` and ``jarvis ppl stop`` load packages from the
        pipeline without calling configure, so fill rules (``state_dir``,
        ``run_dir``) would still be empty. Fills depend only on the placement,
        so a later ``ppl stop`` in another process resolves the same paths.
        With ``prepare``, also write the input files and ``clio-contract.json``
        as configure would.
        """
        if FILLED_KEY in self.config:
            return
        resolved = self._clio_resolve({})
        if prepare:
            self._clio_prepare(resolved)
            self._clio_write_record(self.clio_contract(), resolved)

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        """Write the package's input files. Runs before the record is written."""

    def clio_config(self) -> dict[str, Any]:
        names = {entry["name"] for entry in self.clio_contract().menu}
        return {name: self.config.get(name) for name in names}

    def _clio_write_record(self, contract: Contract, config: Mapping[str, Any]) -> Path:
        document = contract.describe(config, self._clio_placement())
        document["schema"] = RESOLVED_SCHEMA
        document["config"] = dict(config)
        document["inputs"] = contract.input_digests(config)
        document["pkg_id"] = getattr(self, "pkg_id", None)
        path = Path(str(self.shared_dir)) / RECORD_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path

    # -- launching ------------------------------------------------------------

    def clio_executable(self) -> str:
        """The program, found on the PATH the package's install gives (spack load, venv, env)."""
        return self.clio_program

    def _clio_mpi(self, command: str, cwd: str, line_callback=None, check: bool = True) -> dict[str, int]:
        """Run ``command`` under MPI with stdout on the progress and artifact providers.

        ``line_callback`` replaces the runtime callback (wrap it to watch the
        lines too); with ``check`` false the exit codes come back instead of an
        error.
        """
        result = Exec(
            command,
            MpiExecInfo(
                nprocs=int(self.config["nprocs"]),
                ppn=self.clio_ppn(),
                hostfile=self.hostfile,
                env=mpi_safe_env(self.mod_env),
                cwd=cwd,
                line_callback=line_callback if line_callback is not None else self.runtime_line_callback(),
            ),
        ).run()
        codes = dict(result.exit_code)
        failures = {host: code for host, code in codes.items() if code != 0}
        if failures and check:
            raise RuntimeError(f"{self.clio_contract().pkg_type} failed: {failures}")
        return codes

    # -- jarvis-cd deployment contract --------------------------------------

    def _clio_runtime_status(self) -> RuntimeStatus:
        environment = self._deployment_environment()
        program = self.clio_executable()
        if shutil.which(program, path=environment.get("PATH")) is None:
            return RuntimeStatus("unavailable", "software_not_found")
        if self.clio_probe_arguments is None:
            # An MPI solver started outside mpiexec can hang in MPI_Init; finding it is enough.
            return RuntimeStatus("ready", "software_found")
        return probe_program(
            program,
            environment=environment,
            arguments=self.clio_probe_arguments,
            accepted_return_codes=self.clio_probe_return_codes,
            timeout_seconds=10,
        ).status

    def _deployment_contract(self) -> PackageDeploymentContract:
        contract = self.clio_contract()
        status = self._clio_runtime_status()
        requirement = RuntimeRequirement(
            requirement_id=contract.package,
            description=(
                f"{self.clio_executable()} available through PATH from the "
                f"{contract.data['install']['method']} install "
                f"{contract.data['install']['query']!r} (jarvis ppl install)"
            ),
            required_capabilities=self.clio_capabilities,
            available_capabilities=self.clio_capabilities if status.usable else (),
            status=status,
        )
        if contract.kind == "service":
            profile = ExecutionProfile(
                name="service",
                execution_kind="service",
                when=(ConfigurationCondition("nprocs", "greater_than", 0),),
                runtime_requirements=(contract.package,),
                readiness=ReadinessContract(mechanism="progress_event", condition="ready"),
                description=contract.data["summary"],
            )
        else:
            profile = ExecutionProfile(
                name="batch",
                execution_kind="batch",
                when=(ConfigurationCondition("nprocs", "greater_than", 0),),
                runtime_requirements=(contract.package,),
                readiness=ReadinessContract(mechanism="process_exit", condition="successful_exit"),
                description=contract.data["summary"],
            )
        return PackageDeploymentContract(
            package=contract.pkg_type,
            execution_profiles=(profile,),
            runtime_requirements=(requirement,),
        )


class ClioApplication(_ClioPackage, Application):
    """A clio-jarvis batch application."""


class ClioService(_ClioPackage, Service):
    """A clio-jarvis long-running service."""
