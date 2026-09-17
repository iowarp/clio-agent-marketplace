"""Composability-proof tests for the ``earthscope-stations`` A2UI catalog (S7).

docs/design/a2ui-compat-campaign-2026-09.md S7's marketplace half: this pack
ships its own A2UI 0.9.1 catalog (``catalogs/earthscope-stations/``) rather
than depending on any clio-agent or gact-tui source change. These tests prove
the catalog is well-formed against the OFFICIAL shapes clio-schemas vendors —
never against a private re-statement of them — and that the recipe
``instructions.md`` teaches producers is exactly what the catalog allows.

Two separate Python environments are involved, matching the two separate
dependencies these checks exercise (this repository ships neither as its own
dependency — see ``scripts/validate_marketplace_blueprints.py``'s module
docstring for why):

* Every test in this module except
  :func:`test_validate_marketplace_blueprints_script_passes` needs only
  ``clio-schemas`` (>=0.3, unreleased on PyPI at the time of writing — use a
  local checkout)::

      uv run --project /path/to/clio-schemas --with pytest pytest \\
          earthscope-single-agent/tests/test_a2ui_catalog_pack.py

* :func:`test_validate_marketplace_blueprints_script_passes` additionally
  needs ``clio-agent`` importable (it drives the real
  ``validate_agent_blueprint_path`` structural validator, not a
  reimplementation of it), so it imports that dependency lazily and fails
  loudly — never silently skips — when it is not present. Run the full file
  against a clio-agent checkout to exercise it too::

      uv run --project /path/to/clio-agent --with pytest --with clio-schemas \\
          pytest earthscope-single-agent/tests/test_a2ui_catalog_pack.py
"""

from __future__ import annotations

import importlib.resources
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from clio_schemas.a2ui.sidecar import CatalogSidecar
from clio_schemas.a2ui.v0_9_1.catalog_file import CatalogFile
from clio_schemas.a2ui.validation import catalog_validators, message_validator

PACK_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = PACK_ROOT / "catalogs" / "earthscope-stations"
MARKETPLACE_ROOT = PACK_ROOT.parent

_EXPECTED_COMPONENTS = frozenset(
    {"Text", "Column", "Row", "Button", "StationMap", "StationPicker"}
)
#: Fenced ```json blocks may be indented (they sit inside a numbered list in
#: instructions.md), so both fence delimiters tolerate leading whitespace;
#: the captured JSON body itself may stay indented -- JSON whitespace outside
#: string literals is insignificant, so json.loads accepts it as-is.
_JSON_FENCE = re.compile(r"[ \t]*```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _instructions_json_blocks() -> list[dict[str, Any]]:
    """Every fenced ```json block in ``instructions.md``, in document order."""

    text = (CATALOG_DIR / "instructions.md").read_text(encoding="utf-8")
    return [json.loads(match) for match in _JSON_FENCE.findall(text)]


@pytest.fixture(scope="module")
def catalog_file() -> dict[str, Any]:
    return _load_json(CATALOG_DIR / "catalog.json")


@pytest.fixture(scope="module")
def sidecar_raw() -> dict[str, Any]:
    return _load_json(CATALOG_DIR / "catalog.clio.json")


def test_catalog_file_validates_as_catalog_file(catalog_file: dict[str, Any]) -> None:
    """The official 0.9.1 catalog-file shape (clio_schemas.a2ui.v0_9_1.catalog_file)."""

    parsed = CatalogFile.model_validate(catalog_file)
    assert set(parsed.components) == _EXPECTED_COMPONENTS
    assert len(parsed.functions) == 14, "functions must be the Basic 14, verbatim"
    assert parsed.catalogId == "https://iowarp.ai/a2ui/catalogs/earthscope-stations/v1"
    assert {"CatalogComponentCommon", "theme", "MapPoint", "anyComponent", "anyFunction"} <= set(
        parsed.defs_
    )


def test_sidecar_validates_as_catalog_sidecar(sidecar_raw: dict[str, Any]) -> None:
    """The CLIO packaging sidecar (clio_schemas.a2ui.sidecar.CatalogSidecar)."""

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    assert sidecar.protocolVersion == "0.9.1"
    assert sidecar.trust.source == "pack"
    assert sidecar.instructions == "instructions.md"
    assert sidecar.implements["StationMap"].kernel == "clio.map.v1"
    assert sidecar.implements["StationPicker"].kernel == "ChoicePicker"
    assert sidecar.implements["StationPicker"].presets == {"variant": "multipleSelection"}
    for identity_name in ("Text", "Column", "Row", "Button"):
        assert sidecar.implements[identity_name].kernel == identity_name
    assert set(sidecar.events) == {"earthscope.stations.selected"}
    assert sidecar.events["earthscope.stations.selected"].destination == "agent"


def _builtin_component_names() -> frozenset[str]:
    """Every component name the vendored Basic + clio-workspace catalogs implement."""

    a2ui_root = Path(str(importlib.resources.files("clio_schemas") / "schemas" / "a2ui"))
    basic = _load_json(a2ui_root / "v0_9_1" / "catalogs" / "basic" / "catalog.json")
    workspace = _load_json(a2ui_root / "catalogs" / "clio-workspace" / "v1" / "catalog.json")
    return frozenset(basic["components"]) | frozenset(workspace["components"])


def test_every_implements_kernel_names_a_basic_or_workspace_component(
    sidecar_raw: dict[str, Any],
) -> None:
    """Mirrors clio-agent's own install-time gate (a2ui_catalogs/blueprint.py::_load_one)."""

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    builtin_names = _builtin_component_names()
    unimplemented = {
        name: impl.kernel for name, impl in sidecar.implements.items() if impl.kernel not in builtin_names
    }
    assert not unimplemented, f"kernels not implemented by Basic or clio-workspace: {unimplemented}"


def test_station_picker_variant_is_locked_to_multiple_selection(
    catalog_file: dict[str, Any],
) -> None:
    """The preset in the sidecar must match a real ``const`` in the component shape."""

    variant_schema = catalog_file["components"]["StationPicker"]["allOf"][-1]["properties"]["variant"]
    assert variant_schema.get("const") == "multipleSelection"


def test_instructions_example_surface_validates_against_the_catalog(
    catalog_file: dict[str, Any],
) -> None:
    """The exact createSurface/updateComponents/updateDataModel example in instructions.md."""

    blocks = _instructions_json_blocks()
    # The last two fenced blocks before the full example are the recipe's stand-alone
    # `required` check condition and Button `action.event` snippets; the three full
    # protocol messages follow, then the delivered-event context example.
    create_surface, update_components, update_data_model, _event_context = blocks[-4:]

    validator = message_validator("server_to_client", catalog=catalog_file)
    validator.validate(create_surface)
    validator.validate(update_components)
    validator.validate(update_data_model)

    components = update_components["updateComponents"]["components"]
    assert sum(1 for c in components if c.get("id") == "root") == 1
    per_component_validators = catalog_validators(catalog_file)
    for component in components:
        per_component_validators[component["component"]].validate(component)


def test_delivered_event_context_validates_against_context_schema(
    sidecar_raw: dict[str, Any],
) -> None:
    """The example ``earthscope.stations.selected`` payload matches its own context_schema."""

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    context_schema = sidecar.events["earthscope.stations.selected"].context_schema
    assert context_schema is not None

    blocks = _instructions_json_blocks()
    event_context = blocks[-1]
    assert set(event_context) == {"searchId", "stationIds"}
    assert len(event_context["stationIds"]) >= 1
    jsonschema.validate(event_context, context_schema)

    # A structural negative: an empty stationIds array must be rejected (minItems: 1),
    # proving the schema actually constrains rather than merely describing the shape.
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"searchId": "x", "stationIds": []}, context_schema)


def test_validate_marketplace_blueprints_script_passes() -> None:
    """Runs the real offline blueprint validator against this repo (needs clio-agent).

    Deliberately NOT wrapped in a try/except-skip: per this repository's testing
    policy, a test that cannot run is a failure, not a silent pass. See this
    module's docstring for the two-environment split and the exact command to
    run this test under.
    """

    try:
        import clio_agent  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment-dependent, not swallowed
        pytest.fail(
            "clio_agent is not importable in this interpreter -- this test requires a "
            "clio-agent checkout (see this module's docstring for the exact command), "
            f"it does not skip: {exc!r}"
        )

    sys.path.insert(0, str(MARKETPLACE_ROOT / "scripts"))
    import validate_marketplace_blueprints as validator_script  # noqa: PLC0415

    exit_code = validator_script.main([str(MARKETPLACE_ROOT)])
    assert exit_code == 0
