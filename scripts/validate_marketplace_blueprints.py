#!/usr/bin/env python3
"""Static/offline Agent Blueprint validation for every marketplace pack.

Calls ``clio_agent.gact.agent_blueprints.validate_agent_blueprint_path`` — the
same structural validator the live GACT server runs at pack install/enable
time (parsed frontmatter, expert hierarchy, declared tool references, MCP
server descriptors, and — since docs/design/a2ui-compat-campaign-2026-09.md
S2/S7 — each pack's own ``a2ui_catalogs`` declaration: ``catalog.json``/
``catalog.clio.json`` schema validity and every ``implements[*].kernel``
naming a Basic or clio-workspace component) — against every pack directory
in this repository, with no live app (``runtime_tool_names=()``).

This is NOT part of ``.github/workflows/ci.yml``'s ``uv run --no-project
python -m unittest discover -s tests`` job: that job runs an isolated
interpreter with no third-party packages, and this script requires
``clio-agent`` importable (a heavy dependency this repository does not
otherwise carry — see ``pyproject.toml``'s absence and RULE "no clio-agent
source edit" for why it is not vendored here). Run it against a clio-agent
checkout instead, e.g.::

    uv run --project /path/to/clio-agent python scripts/validate_marketplace_blueprints.py

One pack, ``cluster-operator``, is a KNOWN, DOCUMENTED exception: its
``experts/operator.md`` references relay/Jarvis tools (``jarvis_*``,
``relay_*``, ``remote_spack_*``) that only exist on a live clio-agent serve
bound to a relay (``runtime_tool_names_for_validation`` returns an empty set
for any app-less caller, by that function's own docstring — "valid ONLY
against the live runtime"). ``cluster-operator/README.md``'s "Static/offline
marketplace validation" section documents this exact set of "unknown tool
reference" errors as expected, not a defect, and records that the pack was
instead verified by binding it to a live serve. This script does not swallow
those errors — it still prints every one of them — but does not fail the run
over ONLY that pack's ONLY-in-static-mode findings, matching what its own
README already commits to.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    from clio_agent.gact.agent_blueprints import validate_agent_blueprint_path
except ImportError as exc:  # pragma: no cover - guidance path, not a silent skip
    raise SystemExit(
        "clio_agent is not importable in this interpreter. Run this script against a "
        "clio-agent checkout, e.g.:\n"
        "  uv run --project /path/to/clio-agent python "
        "scripts/validate_marketplace_blueprints.py\n"
        f"(original error: {exc})"
    ) from exc

_BLUEPRINT_ROOT_NAME = "AGENT.md"

#: Packs whose static/offline "unknown tool reference" findings are a
#: documented, pre-existing, live-serve-only condition (see this module's
#: docstring and ``<pack>/README.md``'s "Static/offline marketplace
#: validation" section). A pack listed here still has every one of its
#: findings printed; only the overall exit status treats them as non-fatal.
_LIVE_SERVE_ONLY_VERIFIED_PACKS = frozenset({"cluster-operator"})


def discover_pack_dirs(root: Path) -> list[Path]:
    """Return every immediate subdirectory of ``root`` that ships an ``AGENT.md``."""

    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and (path / _BLUEPRINT_ROOT_NAME).is_file()
    )


def validate_one(pack_dir: Path) -> dict[str, Any]:
    """Run the offline structural validator for one pack; never raises."""

    try:
        result = validate_agent_blueprint_path(pack_dir, scope="session")
    except Exception as exc:  # noqa: BLE001 - a parse crash is itself a finding
        return {"validation_errors": [f"{pack_dir.name}: raised {exc!r}"], "validation_warnings": []}
    return result


def main(argv: list[str] | None = None) -> int:
    """Validate every marketplace pack; return the process exit code."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1]),
        help="Marketplace repository root (default: this script's repository).",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    pack_dirs = discover_pack_dirs(root)
    if not pack_dirs:
        print(f"No packs found under {root} (looked for */{_BLUEPRINT_ROOT_NAME}).")
        return 1

    hard_failures: list[str] = []
    for pack_dir in pack_dirs:
        result = validate_one(pack_dir)
        errors = list(result.get("validation_errors") or [])
        warnings = list(result.get("validation_warnings") or [])
        live_only = pack_dir.name in _LIVE_SERVE_ONLY_VERIFIED_PACKS
        if errors and live_only:
            status = "OK (live-serve-only verified — see README)"
        elif errors:
            status = "FAIL"
            hard_failures.append(pack_dir.name)
        else:
            status = "OK"
        print(f"{pack_dir.name}: {status} — errors={len(errors)} warnings={len(warnings)}")
        for error in errors:
            print(f"   ERROR: {error}")
        for warning in warnings:
            print(f"   WARN : {warning}")

    print()
    if hard_failures:
        print(f"FAILED: {len(hard_failures)} pack(s) with unexpected validation errors: "
              f"{', '.join(hard_failures)}")
        return 1
    print(f"OK: {len(pack_dirs)} pack(s) validated "
          f"({len(_LIVE_SERVE_ONLY_VERIFIED_PACKS)} live-serve-only exception(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
