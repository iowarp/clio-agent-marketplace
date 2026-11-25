"""LAMMPS self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

from clio_jarvis.lammps.pkg import RESULT_NAME

_TIME = re.compile(r'Name="TimeValue"')


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    result = json.loads((run_dir / RESULT_NAME).read_text(encoding="utf-8"))
    check("lmp ran the script to the end", result["status"] == "ok", result.get("cause") or "ok")
    steps, interval = int(config["steps"]), int(config["dump_interval"])
    frames = sorted((run_dir / "frames").glob("frame_*.vtp"))
    check("one frame per interval, plus the first", len(frames) == steps // interval + 1, f"{len(frames)} of {steps // interval + 1}")
    timesteps = [int(path.stem.split("_")[1]) for path in frames]
    check(
        "frames are named by timestep",
        timesteps == list(range(0, steps + 1, interval)),
        " ".join(str(step) for step in timesteps),
    )
    check(
        "every frame is a whole PolyData file with its time",
        all(_TIME.search(text := path.read_text(encoding="ascii")) and text.rstrip().endswith("</VTKFile>") for path in frames),
        frames[-1].name if frames else "none",
    )
    check("every frame has all the atoms", result.get("atoms") == 16384 and not result.get("frames_skipped"), f"atoms {result.get('atoms')}")
    check("LAMMPS reported its performance", bool(result.get("performance")), "; ".join(result.get("performance") or []))
    check("no partial frame left in frames/", not list((run_dir / "frames").glob(".*")), "frames/ holds .vtp files only")
    sizes = [path.stat().st_size for path in frames]
    check("frames are about the same size", all(abs(a - b) < 0.05 * a for a, b in itertools.pairwise(sizes)), f"{min(sizes)} to {max(sizes)} bytes" if sizes else "none")
