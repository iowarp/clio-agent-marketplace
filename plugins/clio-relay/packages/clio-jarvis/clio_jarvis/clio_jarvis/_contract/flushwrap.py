"""Run an MPI rank's program with a flusher beside it on the same node.

Usage, as each rank's command under the MPI launcher::

    python flushwrap.py --output DIR [--every SECONDS] [--first NAME ...] [--last NAME ...] -- PROGRAM ARGS...

A solver's I/O library usually writes without syncing, so on a shared file
system the node that writes holds new steps in its page cache and pushes
them back in bursts. A viewer on another machine then sees the run jump many
steps at a time. An ``fsync`` only pushes the dirty pages of the node that
calls it, so the flush has to run where the program writes, which the MPI
launcher alone knows. This wrapper runs there, as every rank. On each node
one rank (the node-local rank 0, from the launcher's environment) forks a
flusher and every rank then becomes ``PROGRAM`` through ``exec``. The
program keeps its process, environment, rank and signals, and its exit
status is the rank's. Without a node-local rank in the environment every
rank flushes, which costs more but is still correct.

Each pass syncs the files matching ``--first`` in ``--output``, then those
named by ``--last``, so the data a step's index names reaches the server
before the index does. The flusher closes the inherited standard streams
so the launcher's output forwarding ends with the program. It stops once
the program has exited, after one last pass.

Only the standard library is used, so the file runs with any Python 3 on the
compute nodes, without the package installed there.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
import time

#: Environment variables in which MPI launchers give a rank's index on its node.
LOCAL_RANK_VARIABLES = (
    "OMPI_COMM_WORLD_LOCAL_RANK",  # Open MPI
    "MPI_LOCALRANKID",  # MPICH and Intel MPI (Hydra)
    "PMI_LOCAL_RANK",
    "PALS_LOCAL_RANKID",  # HPE Cray PALS
    "MV2_COMM_WORLD_LOCAL_RANK",  # MVAPICH2
    "SLURM_LOCALID",  # srun
)


def local_rank(environ=os.environ) -> int | None:
    for name in LOCAL_RANK_VARIABLES:
        value = environ.get(name, "").strip()
        if value.isdigit():
            return int(value)
    return None


def is_node_leader(environ=os.environ) -> bool:
    rank = local_rank(environ)
    return rank is None or rank == 0


def flush_once(output: str, first: list[str], last: list[str]) -> int:
    """Sync this node's dirty pages of the output's files; returns how many files were synced."""
    try:
        names = sorted(os.listdir(output))
    except OSError:
        return 0
    ordered = [name for name in names if any(fnmatch.fnmatch(name, pattern) for pattern in first)]
    ordered += [name for name in last if name not in ordered]
    synced = 0
    for name in ordered:
        try:
            fd = os.open(os.path.join(output, name), os.O_RDONLY)
        except OSError:
            continue
        try:
            os.fsync(fd)
            synced += 1
        except OSError:
            pass
        finally:
            os.close(fd)
    return synced


def flush_loop(output: str, every: float, first: list[str], last: list[str], parent: int) -> None:
    """Flush every ``every`` seconds while ``parent`` lives, then once more."""
    while os.getppid() == parent:
        time.sleep(every)
        flush_once(output, first, last)
    flush_once(output, first, last)


def _detach_streams() -> None:
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    if null > 2:
        os.close(null)


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="flushwrap")
    parser.add_argument("--output", required=True)
    parser.add_argument("--every", type=float, default=1.0)
    parser.add_argument("--first", action="append", default=[])
    parser.add_argument("--last", action="append", default=[])
    parser.add_argument("program", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.program and args.program[0] == "--":
        args.program = args.program[1:]
    if not args.program:
        parser.error("no program to run after --")
    if args.every <= 0:
        parser.error("--every must be positive")
    return args


#: BP5 writes a step's data files first, then the metadata and the index that names them.
BP5_FIRST = ("data.*",)
BP5_LAST = ("md.0", "mmd.0", "md.idx")


def bp5_command(output, program: list[str], every: float = 1.0) -> str:
    """A rank's shell command: ``program`` with a flusher of the BP5 directory ``output`` on its node.

    The wrapper runs with the Python running this function (the one that runs
    JARVIS), named by its absolute path, so the MPI launch can start it on
    any node that shares the file system.
    """
    import shlex

    wrapper = [sys.executable, os.path.abspath(__file__), "--output", str(output), "--every", repr(float(every))]
    for pattern in BP5_FIRST:
        wrapper += ["--first", pattern]
    for name in BP5_LAST:
        wrapper += ["--last", name]
    return shlex.join(wrapper + ["--"] + [str(part) for part in program])


def main(argv: list[str] | None = None) -> None:
    args = parse(sys.argv[1:] if argv is None else argv)
    if is_node_leader():
        parent = os.getpid()
        if os.fork() == 0:
            try:
                _detach_streams()
                flush_loop(args.output, args.every, args.first, args.last, parent)
            finally:
                os._exit(0)
    os.execvp(args.program[0], args.program)


if __name__ == "__main__":
    main()
