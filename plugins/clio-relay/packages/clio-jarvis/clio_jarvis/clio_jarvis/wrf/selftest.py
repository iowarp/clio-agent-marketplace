"""WRF self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import json
from pathlib import Path

from clio_jarvis.wrf.pkg import RESULT_NAME, namelist_value


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    namelist = (run_dir / "namelist.input").read_text(encoding="utf-8")
    check(
        "namelist.input carries the configured run length and history interval",
        (namelist_value(namelist, "run_minutes"), namelist_value(namelist, "history_interval"))
        == (str(config["run_minutes"]), str(config["history_interval"])),
        f"run_minutes {namelist_value(namelist, 'run_minutes')} history_interval {namelist_value(namelist, 'history_interval')}",
    )
    result = json.loads((run_dir / RESULT_NAME).read_text(encoding="utf-8"))
    check("wrf.exe completed", result["status"] == "ok", result.get("cause") or "SUCCESS COMPLETE WRF")
    wanted = int(config["run_minutes"]) // int(config["history_interval"]) + 1
    files = sorted(run_dir.glob("wrfout_d01_*"))
    check("one history file per interval, plus the start", len(files) == wanted, f"{len(files)} of {wanted}")
    check("history files are netCDF", all(_magic(path) in (b"CDF", b"\x89HD") for path in files), files[-1].name if files else "none")


def _magic(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(3)
