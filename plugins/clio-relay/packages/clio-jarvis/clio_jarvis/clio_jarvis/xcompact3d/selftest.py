"""Xcompact3d self-test checks beyond the generic ones in clio_jarvis._contract.selftest."""

from __future__ import annotations

import json
from pathlib import Path


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    run_dir = Path(config["run_dir"])
    case = json.loads((run_dir / "clio-case.json").read_text(encoding="utf-8"))
    check("adios2_config.xml selects BP5", 'BP5' in (run_dir / "adios2_config.xml").read_text(encoding="utf-8"))
    check("BP5 metadata index present", (run_dir / "data.bp5" / "md.idx").is_file(), str(run_dir / "data.bp5"))
    if case["case"] != "body":
        return
    nx, ny, nz = case["grid"]
    xml = (run_dir / "clio-vtk.xml").read_text(encoding="utf-8")
    check("vtk.xml extent lists z, y, x", f'WholeExtent="0 {nz - 1} 0 {ny - 1} 0 {nx - 1}"' in xml, case["grid"])
    check("the body covers grid points", case["solid_voxels"] > 0, case["solid_voxels"])
    stdout = (Path(context["work"]) / "jarvis-ppl-run.log").read_text(encoding="utf-8", errors="replace")
    check("the solver read the body mask", "clio: geometry mask" in stdout)
    forces = run_dir / "forces.dat"
    check("the solver wrote body forces", forces.is_file() and forces.stat().st_size > 0, str(forces))
