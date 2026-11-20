"""Gray-Scott self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import json
from pathlib import Path


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    settings = json.loads((run_dir / "settings.json").read_text(encoding="utf-8"))
    output = context["contract"].output("fields")
    wanted = str(run_dir / "gs.bp")
    check("settings.json writes where the view descriptor points", settings["output"] == wanted, settings["output"])
    check(
        "settings.json carries the configured grid and cadence",
        (settings["L"], settings["steps"], settings["plotgap"]) == (config["L"], config["steps"], config["plotgap"]),
        f"L {settings['L']} steps {settings['steps']} plotgap {settings['plotgap']}",
    )
    check("adios2.xml selects BP5", 'type="BP5"' in (run_dir / "adios2.xml").read_text(encoding="utf-8"), output["format"])
    check("BP5 metadata index present", (Path(wanted) / "md.idx").is_file(), wanted)
