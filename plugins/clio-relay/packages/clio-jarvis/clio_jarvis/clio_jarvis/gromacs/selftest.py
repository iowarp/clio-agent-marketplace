"""GROMACS self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from clio_jarvis.gromacs.pkg import RESULT_NAME, TrrReader


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    result = json.loads((run_dir / RESULT_NAME).read_text(encoding="utf-8"))
    check("the stages, grompp and mdrun all finished", result["status"] == "ok", result.get("cause") or "ok")
    nsteps, interval = int(config["nsteps"]), int(config["frame_interval"])
    frames = sorted((run_dir / "frames").glob("frame_*.vtp"))
    wanted = nsteps // interval + 1
    check("one frame per interval, plus step 0", len(frames) == wanted, f"{len(frames)} of {wanted}")
    steps = [int(path.stem.split("_")[1]) for path in frames]
    check("frames are named by step", steps == list(range(0, nsteps + 1, interval)), " ".join(map(str, steps)))
    trr = TrrReader(run_dir / "md.trr").frames()
    check("md.trr holds the same frames", [frame["step"] for frame in trr] == steps, f"{len(trr)} frames in md.trr")
    times = [frame["time"] for frame in trr]
    check("simulated time grows along the series", all(a < b for a, b in itertools.pairwise(times)), f"{times[0]} to {times[-1]} ps" if times else "none")
    atoms = {frame["natoms"] for frame in trr}
    check("every frame has the same atoms, a whole number of waters", len(atoms) == 1 and next(iter(atoms)) % 3 == 0, f"atoms {sorted(atoms)}")
    check(
        "every frame is a whole PolyData file with its time and elements",
        all('Name="TimeValue"' in (text := path.read_text(encoding="ascii")) and 'Name="element"' in text and text.rstrip().endswith("</VTKFile>") for path in frames),
        frames[-1].name if frames else "none",
    )
    check("mdrun reported its performance", result.get("ns_per_day") is not None, f"{result.get('ns_per_day')} ns/day")
