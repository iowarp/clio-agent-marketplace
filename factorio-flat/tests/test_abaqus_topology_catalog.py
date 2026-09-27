"""Composability proof for the ``abaqus-topology`` A2UI catalog.

Mirrors ``earthscope-single-agent/tests/test_a2ui_catalog_pack.py``: the pack
ships its own catalog, validated against the official shapes clio-schemas
vendors, and every example in ``instructions.md`` is exactly what the catalog
allows. ``TopologyViewport`` aliases ``clio.mesh-viewport.v1``, which exists
from clio-schemas 0.4.0, so these tests need that version (or a checkout)::

    uv run --project /path/to/clio-agent --with pytest \\
        --with /path/to/clio-schemas \\
        pytest factorio-flat/tests/test_abaqus_topology_catalog.py
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
CATALOG_DIR = PACK_ROOT / "catalogs" / "abaqus-topology"
_EXPECTED = {
    "Text", "Column", "Row", "Button", "CheckBox", "ParameterSlider",
    "TopologyViewport", "DesignMetric", "ConvergencePlot",
}
REVIEWED = "abaqus.topology.reviewed"
FIGURE = "abaqus.topology.figure-requested"
_JSON_FENCE = re.compile(r"[ \t]*```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _blocks() -> list[dict[str, Any]]:
    text = (CATALOG_DIR / "instructions.md").read_text(encoding="utf-8")
    return [json.loads(match) for match in _JSON_FENCE.findall(text)]


@pytest.fixture(scope="module")
def catalog_file() -> dict[str, Any]:
    return _load(CATALOG_DIR / "catalog.json")


@pytest.fixture(scope="module")
def sidecar() -> CatalogSidecar:
    return CatalogSidecar.model_validate(_load(CATALOG_DIR / "catalog.clio.json"))


def test_catalog_file_validates(catalog_file: dict[str, Any]) -> None:
    parsed = CatalogFile.model_validate(catalog_file)
    assert set(parsed.components) == _EXPECTED
    assert len(parsed.functions) == 14, "functions must be the Basic 14, verbatim"
    assert parsed.catalogId == "https://iowarp.ai/a2ui/catalogs/abaqus-topology/v1"


def test_sidecar_aliases_the_mesh_viewport_kernel(sidecar: CatalogSidecar) -> None:
    assert sidecar.trust.source == "pack"
    assert sidecar.implements["TopologyViewport"].kernel == "clio.mesh-viewport.v1"
    assert sidecar.implements["DesignMetric"].kernel == "clio.metric.v1"
    assert sidecar.implements["ConvergencePlot"].kernel == "clio.time-series.v1"
    assert sidecar.implements["ParameterSlider"].kernel == "clio.slider.v1"
    assert set(sidecar.events) == {REVIEWED, FIGURE}
    assert all(route.destination == "agent" for route in sidecar.events.values())


def test_every_kernel_is_a_builtin_component(sidecar: CatalogSidecar) -> None:
    """Mirrors clio-agent's install-time gate: aliases must name implemented kernels."""

    root = Path(str(importlib.resources.files("clio_schemas") / "schemas" / "a2ui"))
    basic = _load(root / "v0_9_1" / "catalogs" / "basic" / "catalog.json")
    workspace = _load(root / "catalogs" / "clio-workspace" / "v1" / "catalog.json")
    builtin = set(basic["components"]) | set(workspace["components"])
    missing = {n: i.kernel for n, i in sidecar.implements.items() if i.kernel not in builtin}
    assert not missing, f"kernels not implemented by Basic or clio-workspace: {missing}"


def test_viewport_shape_matches_its_kernel(catalog_file: dict[str, Any]) -> None:
    """The alias carries the kernel's exact property contract, only renamed."""

    root = Path(str(importlib.resources.files("clio_schemas") / "schemas" / "a2ui"))
    workspace = _load(root / "catalogs" / "clio-workspace" / "v1" / "catalog.json")

    def props(component: dict[str, Any]) -> dict[str, Any]:
        entry = next(part for part in component["allOf"] if "properties" in part)
        return {
            name: {k: v for k, v in value.items() if k != "description"}
            for name, value in entry["properties"].items()
            if name != "component"
        }

    alias = catalog_file["components"]["TopologyViewport"]
    kernel = workspace["components"]["clio.mesh-viewport.v1"]
    assert props(alias) == props(kernel)


def _validate_view(catalog_file: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    create, update, data = blocks
    validator = message_validator("server_to_client", catalog=catalog_file)
    for message in (create, update, data):
        validator.validate(message)
    components = update["updateComponents"]["components"]
    per_component = catalog_validators(catalog_file)
    for component in components:
        per_component[component["component"]].validate(component)
    assert sum(1 for c in components if c["id"] == "root") == 1
    return components


def test_compare_view_validates_and_links_both_viewports(catalog_file: dict[str, Any]) -> None:
    blocks = _blocks()
    components = _validate_view(catalog_file, blocks[0:3])
    by_id = {c["id"]: c for c in components}
    views = [c for c in components if c["component"] == "TopologyViewport"]
    assert len(views) == 2
    assert len({view["syncGroup"] for view in views}) == 1, "both views must share one group"
    toggle_path = by_id["stressToggle"]["value"]["path"]
    assert all(view["showField"] == {"path": toggle_path} for view in views)
    assert blocks[2]["updateDataModel"]["value"]["showStress"] is False


def test_history_view_binds_sliders_to_threshold_and_frame(catalog_file: dict[str, Any]) -> None:
    blocks = _blocks()
    components = _validate_view(catalog_file, blocks[4:7])
    by_id = {c["id"]: c for c in components}
    view = by_id["designView"]
    assert view["thresholdField"] == "DENSITY" and view["field"] == "DENSITY"
    assert view["thresholdMin"] == by_id["isoSlider"]["value"]
    assert view["frame"] == by_id["cycleSlider"]["value"]
    context = by_id["figureButton"]["action"]["event"]["context"]
    assert context["camera"] == view["camera"]
    assert context["frame"] == view["frame"] and context["iso"] == view["thresholdMin"]
    model = blocks[6]["updateDataModel"]["value"]
    assert 0 <= model["iso"] <= by_id["isoSlider"]["max"] == view["thresholdMax"] == 1
    assert by_id["isoSlider"]["step"] == 0.01 and by_id["cycleSlider"]["step"] == 1
    assert model["cycle"] <= by_id["cycleSlider"]["max"]


def test_rejects_filesystem_mesh_paths(catalog_file: dict[str, Any]) -> None:
    viewport = catalog_validators(catalog_file)["TopologyViewport"]
    assert not viewport.is_valid(
        {"id": "v", "component": "TopologyViewport", "meshUri": "/scratch/run/optimized.glb"}
    )


@pytest.mark.parametrize(("event", "index"), [(REVIEWED, 3), (FIGURE, 7)])
def test_event_contexts_and_narration(sidecar: CatalogSidecar, event: str, index: int) -> None:
    route = sidecar.events[event]
    context = _blocks()[index]
    jsonschema.validate(context, route.context_schema)
    used = {f for _, f, _, _ in string.Formatter().parse(route.narration) if f}
    assert used <= set(route.context_schema["properties"])
    rendered = render_narration(route, context)
    assert rendered is not None and context["runId"] in rendered


def test_event_schemas_reject_bad_values(sidecar: CatalogSidecar) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"runId": "x", "decision": "maybe"}, sidecar.events[REVIEWED].context_schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"runId": "x", "camera": {"position": [0, 0], "target": [0, 0, 0]}, "frame": 0, "iso": 1.5},
            sidecar.events[FIGURE].context_schema,
        )


def test_pack_blueprint_validates_against_the_real_validator() -> None:
    """The live install-time validator accepts the pack (needs clio-agent importable)."""

    try:
        from clio_agent.gact.agent_blueprints import validate_agent_blueprint_path
    except ImportError as exc:  # pragma: no cover - not swallowed
        pytest.fail(f"clio_agent is not importable in this interpreter: {exc!r}")
        return
    # view_image/view_pdf are registered by the live server only when the
    # configured model reads images/PDFs; pass them as such a deployment does.
    result = validate_agent_blueprint_path(
        PACK_ROOT, scope="session", runtime_tool_names=("view_image", "view_pdf")
    )
    assert result["validation_errors"] == []
    assert result["enabled"] is True
