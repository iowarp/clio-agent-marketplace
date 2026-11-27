"""clio-jarvis command line: validate, describe and self-test packages.

    python -m clio_jarvis validate [PACKAGE ...]
    python -m clio_jarvis describe PACKAGE [--set name=value ...]
    python -m clio_jarvis selftest PACKAGE [--set name=value ...] [--work DIR]

The self-test reads the output with pvpython when ParaView's Spack install is
loaded (``spack load paraview``) in the calling shell.
"""

from __future__ import annotations

import argparse
import json
import sys

from ._contract.spec import REPO_PACKAGES_DIR, ContractError, find_packages, load_contract


def _validate(names: list[str]) -> int:
    dirs = [REPO_PACKAGES_DIR / name for name in names] if names else find_packages()
    status = 0
    for pkg_dir in dirs:
        try:
            contract = load_contract(pkg_dir)
        except ContractError as exc:
            print(f"REFUSED {pkg_dir.name}: part {exc.part}: {exc.reason}")
            status = 1
            continue
        print(f"ok {contract.pkg_type} {contract.version} sha256 {contract.sha256}")
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clio_jarvis", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check every package's contract")
    validate.add_argument("packages", nargs="*")
    describe = commands.add_parser("describe", help="print the document relay reads before a run")
    describe.add_argument("package")
    describe.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    selftest = commands.add_parser("selftest", help="run a package's self-test through jarvis-cd")
    selftest.add_argument("package")
    selftest.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    selftest.add_argument("--work", help="parent directory for the run (default ~/.cache/clio-jarvis-selftest)")
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.packages)

    from ._contract.selftest import parse_overrides

    if args.command == "describe":
        contract = load_contract(REPO_PACKAGES_DIR / args.package)
        print(json.dumps(contract.describe(parse_overrides(args.set)), indent=2, sort_keys=True))
        return 0

    from ._contract.selftest import SelfTest

    report = SelfTest(args.package, overrides=parse_overrides(args.set), work=args.work).run()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
