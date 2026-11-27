"""WarpX self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from clio_jarvis.warpx.pkg import RESULT_NAME, parse_inputs, plotfile_time


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    result = json.loads((run_dir / RESULT_NAME).read_text(encoding="utf-8"))
    check("warpx.3d ran every step", result["status"] == "ok", result.get("cause") or f"step {result.get('step')}")
    wanted = int(config["max_step"]) // int(config["plot_interval"]) + 1
    plotfiles = sorted(path for path in (run_dir / "plotfiles").glob("plt*") if path.is_dir())
    check("one plotfile per interval, plus step 0", len(plotfiles) == wanted, f"{len(plotfiles)} of {wanted}")
    check(
        "every plotfile is whole",
        all((path / "Header").is_file() and (path / "Level_0" / "Cell_H").is_file() for path in plotfiles),
        plotfiles[-1].name if plotfiles else "none",
    )
    names = [path.name for path in plotfiles]
    steps = [int(name[3:]) for name in names]
    check(
        "plotfiles are named by step",
        steps == list(range(0, int(config["max_step"]) + 1, int(config["plot_interval"]))),
        " ".join(names),
    )
    read = [plotfile_time(path) for path in plotfiles]
    times = [t for t in read if t is not None]
    check(
        "simulated time grows along the series",
        len(times) == len(read) and all(a < b for a, b in itertools.pairwise(times)),
        f"{times[0]} to {times[-1]}" if times else "none",
    )
    left = list((run_dir / "writing").iterdir()) if (run_dir / "writing").is_dir() else []
    check("no plotfile left half published", not left, " ".join(path.name for path in left) or "writing/ empty")
    used = parse_inputs((run_dir / "warpx_used_inputs").read_text(encoding="utf-8", errors="replace"))
    check(
        "WarpX ran the configured length",
        used.get("max_step") == str(config["max_step"]),
        f"max_step {used.get('max_step')}",
    )
