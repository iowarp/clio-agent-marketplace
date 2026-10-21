"""Composability-proof tests for the ``earthscope-stations`` A2UI catalog.

The earthscope-skills plugin ships its own A2UI 0.9.1 catalog
(``ai.iowarp.clio/a2ui/earthscope-stations/``) rather than depending on any
clio-agent or gact-tui source change. These tests prove the catalog is
well-formed against the OFFICIAL shapes clio-schemas vendors -- never against a
private re-statement of them -- that the recipe ``instructions.md`` teaches
producers is exactly what the catalog allows, and that clio-agent's plugin
catalog loader and generated catalog skill accept it. They need clio-agent
(which brings clio-schemas) importable::

    uv run --with "clio-agent @ git+https://github.com/iowarp/clio-agent@develop" \\
        --with pytest pytest plugins/earthscope-skills/tests

CI runs exactly this (see ``.github/workflows/ci.yml``).
"""

from __future__ import annotations

import importlib.resources
import json
import re
import string
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from clio_schemas.a2ui.sidecar import CatalogSidecar, render_narration
from clio_schemas.a2ui.v0_9_1.catalog_file import CatalogFile
from clio_schemas.a2ui.validation import catalog_validators, message_validator

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = PLUGIN_ROOT / "ai.iowarp.clio" / "a2ui" / "earthscope-stations"

_EXPECTED_COMPONENTS = frozenset({"Text", "Column", "Row", "Button", "StationMap", "StationPicker"})
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
        name: impl.kernel
        for name, impl in sidecar.implements.items()
        if impl.kernel not in builtin_names
    }
    assert not unimplemented, f"kernels not implemented by Basic or clio-workspace: {unimplemented}"


def test_station_picker_variant_is_locked_to_multiple_selection(
    catalog_file: dict[str, Any],
) -> None:
    """The preset in the sidecar must match a real ``const`` in the component shape."""

    variant_schema = catalog_file["components"]["StationPicker"]["allOf"][-1]["properties"][
        "variant"
    ]
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


def test_sidecar_narration_parses_under_0_3_2(sidecar_raw: dict[str, Any]) -> None:
    """The event's ``narration`` (clio-schemas 0.3.2) parses on this sidecar."""

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    route = sidecar.events["earthscope.stations.selected"]
    assert route.narration is not None
    assert "{stationIds}" in route.narration
    assert "{searchId}" in route.narration


def test_narration_placeholders_are_all_context_schema_properties(
    sidecar_raw: dict[str, Any],
) -> None:
    """Every ``{placeholder}`` in the narration names a declared context field.

    ``CatalogSidecar`` already enforces this at parse time (a mismatch would
    have raised in the fixture above); this test re-derives the placeholder
    set independently and asserts it against ``context_schema.properties``
    directly, so a future relaxation of that validator would still be caught
    here.
    """

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    route = sidecar.events["earthscope.stations.selected"]
    assert route.context_schema is not None
    properties = set(route.context_schema["properties"])

    used = {
        field_name.split(".", 1)[0].split("[", 1)[0]
        for _, field_name, _, _ in string.Formatter().parse(route.narration)
        if field_name
    }
    assert used, "narration should reference at least one context field"
    assert used <= properties


def test_render_narration_over_worked_example_context(
    sidecar_raw: dict[str, Any],
) -> None:
    """``render_narration`` over instructions.md's worked-example context.

    The delivered-event example (the last fenced JSON block) is
    ``{"searchId": "earthscope-la-20260917", "stationIds": ["CI01", "CI02"]}``;
    rendering must embed the searchId verbatim and the station ids as a
    compact JSON array (``["CI01","CI02"]``-style), not a Python repr.
    """

    sidecar = CatalogSidecar.model_validate(sidecar_raw)
    route = sidecar.events["earthscope.stations.selected"]

    event_context = _instructions_json_blocks()[-1]
    assert set(event_context) == {"searchId", "stationIds"}

    rendered = render_narration(route, event_context)
    assert rendered is not None
    assert event_context["searchId"] in rendered
    assert json.dumps(event_context["stationIds"], separators=(",", ":")) in rendered
    assert "{stationIds}" not in rendered
    assert "{searchId}" not in rendered


def test_generated_catalog_skill_states_the_catalog_json_catalog_id() -> None:
    """The station catalog's id reaches the model through clio-agent's GENERATED
    catalog skill (never hand-typed in ``instructions.md``): the plugin loader
    records the catalog, the plugin catalog loader accepts it, and the generated
    skill body states ``catalog.json``'s own ``catalogId``.
    """

    from clio_agent.gact.a2ui_catalogs.plugin import installed_plugin_catalogs
    from clio_agent.gact.a2ui_catalogs.skills import generate_catalog_skill_body
    from clio_agent.plugins.loader import load_plugin

    record = load_plugin(PLUGIN_ROOT, marketplace="test", trusted=True)
    assert not record.errors
    assert [catalog.id for catalog in record.catalogs if catalog.path] == ["earthscope-stations"]
    catalog_id = _load_json(CATALOG_DIR / "catalog.json")["catalogId"]
    (entry,) = installed_plugin_catalogs([record])
    body = generate_catalog_skill_body(entry, is_default=False)
    assert entry.catalog_id == catalog_id
    assert f"Catalog id: `{catalog_id}`" in body
    assert f'catalog_id="{catalog_id}"' in body
    assert (
        catalog_id
        not in (CATALOG_DIR / "instructions.md")
        .read_text(encoding="utf-8")
        .split("## One complete example surface")[0]
    ), "the catalogId belongs to the generated skill, not hand-typed prose"
