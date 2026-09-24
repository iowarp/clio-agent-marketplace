"""Composability-proof tests for the ``earthscope-stations`` A2UI catalog (S7).

docs/design/a2ui-compat-campaign-2026-09.md S7's marketplace half: this pack
ships its own A2UI 0.9.1 catalog (``catalogs/earthscope-stations/``) rather
than depending on any clio-agent or gact-tui source change. These tests prove
the catalog is well-formed against the OFFICIAL shapes clio-schemas vendors —
never against a private re-statement of them — and that the recipe
``instructions.md`` teaches producers is exactly what the catalog allows.

Two separate Python environments are involved, matching the two separate
dependencies these checks exercise (this repository ships neither as its own
dependency):

* Every test in this module except
  :func:`test_pack_blueprint_validates_against_the_real_validator` and
  :func:`test_manifest_declares_a_pep440_clio_agent_floor` needs only
  ``clio-schemas`` (>=0.3, unreleased on PyPI at the time of writing — use a
  local checkout)::

      uv run --project /path/to/clio-schemas --with pytest pytest \\
          earthscope-single-agent/tests/test_a2ui_catalog_pack.py

* :func:`test_pack_blueprint_validates_against_the_real_validator` and
  :func:`test_manifest_declares_a_pep440_clio_agent_floor` additionally need
  ``clio-agent`` importable (the former drives the REAL ``clio_agent.gact.
  agent_blueprints.validate_agent_blueprint_path`` structural validator
  directly — the same one the live GACT server runs at pack install/enable
  time — never a reimplementation of it; the latter parses ``AGENT.md`` with
  clio-agent's own blueprint parser and its declared ``requires.clio_agent``
  floor with ``packaging.specifiers.SpecifierSet`` — a dependency clio-agent
  itself brings transitively, never pinned separately by this repo). Both
  import their dependency lazily and fail loudly — never silently skip —
  when it is not present. Run the full file against a clio-agent checkout to
  exercise them too::

      uv run --project /path/to/clio-agent --with pytest --with clio-schemas \\
          pytest earthscope-single-agent/tests/test_a2ui_catalog_pack.py

  CI runs exactly this second form (see ``.github/workflows/ci.yml``'s
  ``a2ui-catalog-pack`` job) against clio-agent's ``develop`` branch.
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

PACK_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = PACK_ROOT / "catalogs" / "earthscope-stations"

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


def _declared_clio_agent_floor() -> str:
    """The ``requires.clio_agent`` specifier declared in ``AGENT.md``'s frontmatter."""

    from clio_agent.gact.agent_blueprints import parse_agent_blueprint_root

    blueprint = parse_agent_blueprint_root(PACK_ROOT, scope="session")
    requires = blueprint.metadata.get("requires")
    assert isinstance(requires, dict)
    floor = requires.get("clio_agent")
    assert isinstance(floor, str) and floor.strip()
    return floor


def test_pack_blueprint_validates_against_the_real_validator() -> None:
    """Runs clio-agent's REAL structural validator against this pack (needs clio-agent).

    Asserts the ``requires.clio_agent`` floor contract keyed on two facts about
    the running clio-agent, never on an environment flag: whether it enforces
    floors at all (the ``clio_agent.gact.agent_blueprint_requires`` owner module
    exists, campaign slice S8) and ``clio_agent.__version__`` against the floor.

    * enforcing, at or above the floor: installs clean -- no errors, no warnings,
      enabled (the release that carries the floor);
    * enforcing, below the floor: refused with exactly the typed
      ``blueprint_requires_newer_clio_agent`` error, no warnings, not enabled
      (develop between the S8 merge and the release bump);
    * not enforcing: a clio-agent that predates floors ignores the key and
      installs the pack clean (develop before S8 lands) -- and such a build MUST
      be below the floor, otherwise the release shipped without the enforcement
      the pack relies on.

    None of the branches skips.

    Calls ``clio_agent.gact.agent_blueprints.validate_agent_blueprint_path`` directly
    -- the exact function the live GACT server runs at pack install/enable time, never
    a marketplace-side reimplementation of it (a prior version of this module shipped
    a duplicate ``scripts/validate_marketplace_blueprints.py`` that wrapped this same
    call and then silently downgraded one pack's errors to "OK"; that script and its
    silent-fallback exemption are deleted -- this test asserts the real function's
    output directly, with no exemption of any kind).

    Deliberately NOT wrapped in a try/except-skip: per this repository's testing
    policy, a test that cannot run is a failure, not a silent pass. See this module's
    docstring for the two-environment split and the exact command to run this test
    under.
    """

    try:
        import importlib.util

        from clio_agent import __version__ as clio_agent_version
        from clio_agent.gact.agent_blueprints import validate_agent_blueprint_path
        from packaging.specifiers import SpecifierSet
    except ImportError as exc:  # pragma: no cover - environment-dependent, not swallowed
        pytest.fail(
            "clio_agent is not importable in this interpreter -- this test requires a "
            "clio-agent checkout (see this module's docstring for the exact command), "
            f"it does not skip: {exc!r}"
        )
        return

    result = validate_agent_blueprint_path(PACK_ROOT, scope="session")
    floor = _declared_clio_agent_floor()
    satisfies_floor = SpecifierSet(floor).contains(clio_agent_version)
    enforces_floors = (
        importlib.util.find_spec("clio_agent.gact.agent_blueprint_requires") is not None
    )

    if enforces_floors and satisfies_floor:
        assert result["validation_errors"] == []
        assert result["validation_warnings"] == []
        assert result["enabled"] is True
    elif enforces_floors:
        assert result["validation_errors"] == [
            "earthscope-single-agent: blueprint_requires_newer_clio_agent: "
            f"requires clio_agent{floor}, running {clio_agent_version}"
        ]
        assert result["validation_warnings"] == []
        assert result["enabled"] is False
    else:
        assert not satisfies_floor, (
            f"clio-agent {clio_agent_version} satisfies {floor!r} but does not carry "
            "the floor enforcement (clio_agent.gact.agent_blueprint_requires) -- the "
            "release shipped without the semantics this pack's floor relies on"
        )
        assert result["validation_errors"] == []
        assert result["validation_warnings"] == []
        assert result["enabled"] is True


def test_manifest_declares_a_pep440_clio_agent_floor() -> None:
    """``AGENT.md``'s ``requires.clio_agent`` floor is a real, meaningful specifier.

    Parses the manifest with clio-agent's OWN blueprint parser (never a private
    reimplementation of frontmatter parsing) and the declared floor with
    ``packaging.specifiers.SpecifierSet``. ``tests/test_earthscope_single_agent_
    policy.py`` keeps a dependency-free companion check (the key exists and is a
    non-empty string) for CI's bare no-deps job; this test is the one that proves
    the value actually parses as PEP 440 and means what the AGENT.md comment next
    to it claims (admits 0.9.4.17, the first release reading the per-agent
    ``a2ui_catalogs`` list form, and excludes 0.9.4.16, which would silently drop
    the pack catalog).

    Deliberately NOT wrapped in a try/except-skip -- see this module's docstring.
    """

    try:
        from clio_agent.gact.agent_blueprints import parse_agent_blueprint_root
        from packaging.specifiers import SpecifierSet
    except ImportError as exc:  # pragma: no cover - environment-dependent, not swallowed
        pytest.fail(
            "clio_agent/packaging are not importable in this interpreter -- this "
            "test requires a clio-agent checkout (see this module's docstring for "
            f"the exact command), it does not skip: {exc!r}"
        )
        return

    blueprint = parse_agent_blueprint_root(PACK_ROOT, scope="session")
    requires = blueprint.metadata.get("requires")
    assert isinstance(requires, dict)
    floor = requires.get("clio_agent")
    assert isinstance(floor, str) and floor.strip()

    spec = SpecifierSet(floor)
    assert spec.contains("0.9.4.17"), f"{floor!r} should admit 0.9.4.17 (first list-form release)"
    assert spec.contains("0.9.5"), f"{floor!r} should admit 0.9.5"
    assert not spec.contains("0.9.4.16"), f"{floor!r} should exclude 0.9.4.16 (drops the list form)"
    assert not spec.contains("0.9.4"), f"{floor!r} should exclude 0.9.4"
