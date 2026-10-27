"""The hidden-law-bench MCP server: ``apparatus``, ``measure``, ``history``.

Every ``measure`` result carries a readings event in its result ``_meta``
(``ai.iowarp.clio/ui_event``), which CLIO records for the UI and never shows the
model; the first one also carries the ``Readings`` component of this plugin's
``bench`` catalog. Readings are kept per study (the root of the calling session's
task tree, stamped by CLIO in each call's ``_meta`` as ``ai.iowarp.clio/caller``) and
labelled with the branch that took them.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from hidden_law_bench.law import CYCLES, INPUTS, NOISE_S, Law, digest, draw_law

CALLER_META_KEY = "ai.iowarp.clio/caller"
UI_EVENT_META_KEY = "ai.iowarp.clio/ui_event"
CATALOG_ID = "https://iowarp.ai/a2ui/catalogs/bench/v1"
VIEW = "hidden-law-bench/readings"
MAX_REPEATS = 20
_ROOT = Path(os.environ.get("PLUGIN_ROOT") or Path(__file__).resolve().parents[3])
_CATALOG = _ROOT / "ai.iowarp.clio" / "a2ui" / "bench"


def caller(ctx: Context | None) -> dict[str, str]:
    """``{"session", "root"}`` of the calling CLIO session, or ``{}``."""

    try:
        meta = ctx.request_context.meta if ctx is not None else None  # type: ignore[union-attr]
    except (AttributeError, LookupError, ValueError):
        return {}
    if meta is None:
        return {}
    data = meta.model_dump(by_alias=True) if hasattr(meta, "model_dump") else dict(meta)
    value = data.get(CALLER_META_KEY) or {}
    return {k: str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def validate(settings: Any) -> dict[str, float]:
    """Every input named once, numeric and in range; anything else is a tool error."""

    if not isinstance(settings, dict):
        raise ToolError("settings_invalid: settings is an object of input -> value")
    unknown = sorted(set(settings) - set(INPUTS))
    missing = sorted(set(INPUTS) - set(settings))
    if unknown or missing:
        raise ToolError(f"settings_invalid: unknown {unknown}, missing {missing}")
    clean: dict[str, float] = {}
    for name, value in settings.items():
        unit, low, high, _ref = INPUTS[name]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ToolError(f"settings_invalid: {name} must be a number in {unit}")
        if not low <= float(value) <= high:
            raise ToolError(f"out_of_range: {name}={value} {unit} is outside [{low}, {high}]")
        clean[name] = float(value)
    return clean


def readings_component() -> dict[str, Any]:
    spec = json.loads((_CATALOG / "readings_spec.json").read_text(encoding="utf-8"))
    return {"id": "readings", "component": "Readings", "spec": spec, "title": "Bench readings"}


class Apparatus:
    """The bench: the hidden law and every reading taken, per study."""

    def __init__(self, secret: str) -> None:
        self._secret = secret
        self._law: Law = draw_law(secret)
        self.readings: dict[str, list[dict[str, Any]]] = {}
        self._count = 0

    def measure(
        self, settings: dict[str, float], repeats: int, branch: str, study: str
    ) -> list[dict[str, Any]]:
        period = self._law.period(settings)
        taken = []
        for _ in range(repeats):
            self._count += 1
            noise = random.Random(digest(self._secret, f"noise:{self._count}")).gauss(0, NOISE_S)
            taken.append(
                {
                    "reading": self._count,
                    "branch": branch,
                    **settings,
                    "ten_cycles_s": round(CYCLES * period + noise, 4),
                }
            )
        self.readings.setdefault(study, []).extend(taken)
        return taken


def create_server(secret: str | None = None) -> FastMCP:
    bench = Apparatus(secret if secret is not None else os.environ.get("BENCH_SECRET_SEED", ""))
    shown: set[str] = set()
    mcp = FastMCP("bench")

    @mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
    def apparatus() -> dict[str, Any]:
        """The bench: its controllable inputs with units and ranges, what is measured,
        and the stated measurement noise."""

        return {
            "inputs": {
                name: {"unit": unit, "min": low, "max": high}
                for name, (unit, low, high, _ref) in INPUTS.items()
            },
            "measures": {
                "ten_cycles_s": f"time for {CYCLES} cycles of the swinging arm, in seconds"
            },
            "noise": {"ten_cycles_s": {"distribution": "gaussian", "sd_s": NOISE_S}},
            "settings": "measure takes every input, by name, in its unit",
        }

    @mcp.tool
    def measure(settings: dict[str, Any], ctx: Context, repeats: int = 1) -> ToolResult:
        """Take readings at settings (every input, by name). One noisy reading of the
        time for ten cycles per repeat. Out-of-range settings are an error."""

        clean = validate(settings)
        if not 1 <= int(repeats) <= MAX_REPEATS:
            raise ToolError(f"repeats_invalid: repeats is 1 to {MAX_REPEATS}")
        who = caller(ctx)
        study = who.get("root") or "default"
        taken = bench.measure(clean, int(repeats), who.get("session", ""), study)
        event: dict[str, Any] = {
            "view": VIEW,
            "catalog": CATALOG_ID,
            "key": f"r{taken[0]['reading']}",
            "group": who.get("session", ""),
            "rows": [{**row, "period_s": row["ten_cycles_s"] / CYCLES} for row in taken],
        }
        if study not in shown:
            shown.add(study)
            event["component"] = readings_component()
        payload = {"readings": [{k: v for k, v in r.items() if k != "branch"} for r in taken]}
        return ToolResult(
            content=[TextContent(type="text", text=json.dumps(payload))],
            structured_content=payload,
            meta={UI_EVENT_META_KEY: event},
        )

    @mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
    def history(ctx: Context) -> dict[str, Any]:
        """Every reading this study has taken, by branch."""

        study = caller(ctx).get("root") or "default"
        by_branch: dict[str, list[dict[str, Any]]] = {}
        for row in bench.readings.get(study, []):
            by_branch.setdefault(row["branch"] or "unknown", []).append(
                {k: v for k, v in row.items() if k != "branch"}
            )
        return {"branches": by_branch, "count": sum(len(v) for v in by_branch.values())}

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
