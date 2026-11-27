"""Tell a network library's fallback warnings from a failure.

UCX and libfabric probe every network device on a node. When a fast device
(InfiniBand, RoCE, Omni-Path) is missing or down they print a warning, pick
another transport (often TCP or shared memory) and the job goes on. The
warning sits next to the solver's last lines, where it reads like the reason
a run failed, though the ranks communicated without it. This module picks
those lines out so a package can report them as information, with the
transport the library offered instead, and never as a cause.

Only warnings are matched: an error line from these libraries can be fatal
and stays with the failure evidence.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Mapping

#: UCX's own log line at WARN level, e.g. "ucp_context.c:1081 UCX  WARN  network device 'mlx5_0:1' is not available".
UCX_WARN = re.compile(r"\bUCX\s+WARN\b")
#: libfabric's log line at warn level, e.g. "libfabric:1234:1700000000::verbs:fabric:vrb_get_info():123<warn> ...".
LIBFABRIC_WARN = re.compile(r"\blibfabric:[^\s]*<warn>")
#: Open MPI's notice that it skips an InfiniBand or RoCE port it cannot use.
OPENFABRICS_SKIP = re.compile(
    r"(no OpenFabrics connection schemes reported|openib BTL \(OpenFabrics support\) will be disabled|"
    r"OpenFabrics device found, but there are no active ports)",
    re.IGNORECASE,
)
#: A device or transport the line names as missing, e.g. 'mlx5_0:1' or transport 'rc'.
UNAVAILABLE = re.compile(r"(?:device|transport|interface)\s+'([^']+)'\s+(?:is\s+)?not available", re.IGNORECASE)
BARE_UNAVAILABLE = re.compile(r"\b([A-Za-z][\w.-]*:\d+)\s+(?:is\s+)?not available", re.IGNORECASE)
#: What UCX offers instead: "please use one or more of: 'eno1'(tcp), 'lo'(tcp)".
OFFERED = re.compile(r"'([^']+)'\(([^)]+)\)")

#: Launch settings that choose the transport, reported so a reader sees what was asked for.
SETTINGS = (
    "UCX_TLS",
    "UCX_NET_DEVICES",
    "FI_PROVIDER",
    "OMPI_MCA_pml",
    "OMPI_MCA_btl",
    "OMPI_MCA_mtl",
    "I_MPI_FABRICS",
    "I_MPI_OFI_PROVIDER",
    "MPICH_OFI_PROVIDER",
)

NOTE = (
    "Informational: the network library could not use a device it probed and fell back to "
    "another transport, and the ranks went on communicating. These lines are not the cause "
    "of the run's result and do not call for a change to the site's network settings."
)
NOTE_EARLY = (
    "Informational: the network library could not use a device it probed and offered another "
    "transport. A warning like this is printed by runs that succeed too, so it does not explain "
    "why this launch stopped; the failure is in the other lines. Do not change the site's "
    "network settings on the strength of these lines alone."
)


def library(line: str) -> str | None:
    """``ucx``, ``libfabric`` or ``openfabrics`` when ``line`` is a transport fallback warning."""
    if UCX_WARN.search(line):
        return "ucx"
    if LIBFABRIC_WARN.search(line):
        return "libfabric"
    if OPENFABRICS_SKIP.search(line):
        return "openfabrics"
    return None


class TransportNotes:
    """Collects fallback warnings from a launch's output; thread safe."""

    def __init__(self, keep: int = 5) -> None:
        self.keep = keep
        self.lock = threading.Lock()
        self.libraries: list[str] = []
        self.unavailable: list[str] = []
        self.offered: dict[str, list[str]] = {}
        self.lines: list[str] = []
        self.count = 0

    def observe(self, line: str) -> bool:
        """Record ``line`` when it is a fallback warning; True if it was one."""
        which = library(line)
        if which is None:
            return False
        with self.lock:
            self.count += 1
            if which not in self.libraries:
                self.libraries.append(which)
            for pattern in (UNAVAILABLE, BARE_UNAVAILABLE):
                for name in pattern.findall(line):
                    if name not in self.unavailable:
                        self.unavailable.append(name)
            if "use one or more of" in line:
                for device, kind in OFFERED.findall(line.split("use one or more of", 1)[1]):
                    devices = self.offered.setdefault(kind, [])
                    if device not in devices and len(devices) < self.keep:
                        devices.append(device)
            if len(self.lines) < self.keep and line not in self.lines:
                self.lines.append(line)
        return True

    def report(self, env: Mapping[str, Any] | None = None, *, progressed: bool = True) -> dict[str, Any] | None:
        """The ``transport`` block of a run result, or None when no fallback was seen.

        ``progressed`` says the ranks got past start-up, so the fallback carried their traffic.
        """
        with self.lock:
            if not self.count:
                return None
            kinds = list(self.offered)
            if len(kinds) == 1:
                used = f"{kinds[0]} (the only transport the library offered instead)"
            elif kinds:
                used = f"one of {', '.join(kinds)} (the library offered these instead)"
            else:
                used = "a transport other than the ones named unavailable; the library does not say which at its default log level"
            settings = {name: str(env[name]) for name in SETTINGS if env and env.get(name) not in (None, "")}
            return {
                "fallback": True,
                "libraries": list(self.libraries),
                "unavailable": list(self.unavailable),
                "offered": {kind: list(devices) for kind, devices in self.offered.items()},
                "used": used,
                "launch_settings": settings,
                "warning_lines": self.count,
                "examples": list(self.lines),
                "note": NOTE if progressed else NOTE_EARLY,
            }
