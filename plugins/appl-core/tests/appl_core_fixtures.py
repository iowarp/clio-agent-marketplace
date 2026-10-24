"""Test helpers for the appl-core eval tooling tests.

The synthetic bundle (an invented export with one planted instance of each
onboarding trap) is the one the shared ``data-onboarding`` plugin tests its
scripts on; it is loaded from that plugin's test fixtures rather than copied.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PACK = Path(__file__).resolve().parents[1]
PLUGINS = PACK.parent


def load_script(relative: str, name: str) -> ModuleType:
    """Import a script by path relative to this plugin (scripts are not a package)."""

    path = PACK / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_shared = load_script(
    "../data-onboarding/tests/onboarding_fixtures.py", "appl_core_onboarding_fixtures"
)
FLOAT_MAX = _shared.FLOAT_MAX
build_bundle = _shared.build_bundle
tree_hash = _shared.tree_hash
