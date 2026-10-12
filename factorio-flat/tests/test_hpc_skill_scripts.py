"""Tests for the bundled checks of the morphorm and hpc-batch-jobs skills.

``diag_summary.py`` and ``xml_params.py`` are standard library only.
``exo_summary.py`` needs netCDF4 and is skipped without it. ``wait_job.sh``
runs against fake ``squeue``/``sacct`` commands put first on ``PATH``, so no
Slurm installation is needed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[1] / "skills"
MORPHORM = SKILLS / "morphorm" / "scripts"
WAIT_JOB = SKILLS / "hpc-batch-jobs" / "scripts" / "wait_job.sh"


def _run(*args: str | Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env, timeout=60)


DIAGNOSTICS = """Iter  F-count  F(X)  Norm(F')  H1(X)
  1  1  1.000e+00  2.0e-01  0.0
  2  2  8.000e-01  1.0e-01  0.0
  3  3  7.500e-01  5.0e-02  0.0
Optimization stopped: maximum number of iterations reached
"""


def test_diag_summary_reports_rows_and_restart_comparison(tmp_path: Path) -> None:
    diag = tmp_path / "diagnostics.txt"
    diag.write_text(DIAGNOSTICS)
    out = _run(sys.executable, MORPHORM / "diag_summary.py", diag, "--rows", "2", "--compare-first-to", "0.8")
    assert out.returncode == 0, out.stderr
    rep = json.loads(out.stdout)
    assert rep["iteration_rows"] == 3
    assert (rep["first_iter"], rep["last_iter"]) == (1, 3)
    assert rep["first_objective"] == pytest.approx(1.0)
    assert rep["last_objective"] == pytest.approx(0.75)
    assert len(rep["last_rows"]) == 2
    assert rep["first_vs_given_rel_diff"] == pytest.approx(0.25)
    assert any("maximum number of iterations" in line for line in rep["non_row_lines"])


def test_xml_params_lists_settings_and_flags_missing_and_unparsable(tmp_path: Path) -> None:
    (tmp_path / "interface.xml").write_text(
        '<?xml version="1.0"?>\n<Optimizer><Convergence><MaxIterations>50</MaxIterations></Convergence></Optimizer>\n'
    )
    # Several top-level elements, as XMLGenerator writes some files.
    (tmp_path / "deck.xml").write_text(
        '<?xml version="1.0"?>\n<ParameterList name="Problem"><Parameter name="Symmetry Plane Sides" value="{ss_sym}"/>'
        "</ParameterList>\n<ParameterList name=\"Other\"/>\n"
    )
    (tmp_path / "broken.xml").write_text("<a><b></a>")
    out = _run(sys.executable, MORPHORM / "xml_params.py", tmp_path, "symmetry", "maxiterations")
    assert out.returncode == 0, out.stderr
    assert "Symmetry Plane Sides\t{ss_sym}" in out.stdout
    assert "MaxIterations\t50" in out.stdout
    assert "UNPARSABLE\tbroken.xml" in out.stderr
    missing = _run(sys.executable, MORPHORM / "xml_params.py", tmp_path, "length scale")
    assert missing.returncode == 1
    assert "MISSING\tlength scale" in missing.stderr


def test_exo_summary_reports_mesh_and_checks_expectations(tmp_path: Path) -> None:
    netCDF4 = pytest.importorskip("netCDF4")
    np = pytest.importorskip("numpy")
    mesh = tmp_path / "mesh.exo"
    ds = netCDF4.Dataset(mesh, "w")
    for name, size in {"num_nodes": 8, "num_elem": 1, "num_dim": 3, "num_el_blk": 1, "len_string": 33,
                       "num_el_in_blk1": 1, "num_nod_per_el1": 8, "num_node_sets": 1, "num_nod_ns1": 4,
                       "time_step": None}.items():
        ds.createDimension(name, size)
    for axis, values in zip(("coordx", "coordy", "coordz"),
                            ([0, 1, 1, 0, 0, 1, 1, 0], [0, 0, 1, 1, 0, 0, 1, 1], [0, 0, 0, 0, 2, 2, 2, 2])):
        ds.createVariable(axis, "f8", ("num_nodes",))[:] = values
    connect = ds.createVariable("connect1", "i4", ("num_el_in_blk1", "num_nod_per_el1"))
    connect[:] = np.arange(1, 9).reshape(1, 8)
    connect.elem_type = "HEX8"
    for var, dim, name in (("eb_names", "num_el_blk", "design"), ("ns_names", "num_node_sets", "fixed")):
        names = ds.createVariable(var, "S1", (dim, "len_string"))
        names[0, :] = np.array([c.encode() for c in name.ljust(33, "\0")], dtype="S1")
    ds.close()

    out = _run(sys.executable, MORPHORM / "exo_summary.py", mesh, "--expect", "num_elem=1",
               "block:design:type=HEX8", "nodeset:fixed=4", "bbox_max=1,1,2")
    assert out.returncode == 0, out.stdout + out.stderr
    rep = json.loads(out.stdout)
    assert rep["expect_ok"] is True
    assert rep["blocks"] == [{"name": "design", "type": "HEX8", "elems": 1, "nodes_per_elem": 8}]
    wrong = _run(sys.executable, MORPHORM / "exo_summary.py", mesh, "--expect", "num_elem=2")
    assert wrong.returncode == 1
    assert json.loads(wrong.stdout)["expect_failures"][0]["key"] == "num_elem"


@pytest.fixture
def fake_slurm(tmp_path: Path):
    """Fake squeue/sacct whose answers come from files the test writes."""
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "squeue").write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/squeue.out" 2>/dev/null\n')
    (bin_dir / "sacct").write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/sacct.out" 2>/dev/null\n')
    for tool in ("squeue", "sacct"):
        (bin_dir / tool).chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return tmp_path, env


def test_wait_job_reports_a_finished_job(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.out").write_text("COMPLETED|0:0|00:10:00|node1\n")
    out = _run("bash", WAIT_JOB, "123", "5", "", "1", env=env)
    assert out.returncode == 0, out.stderr
    assert "job 123 finished: COMPLETED|0:0|00:10:00|node1" in out.stdout


def test_wait_job_returns_3_for_a_running_job_at_the_limit(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "squeue.out").write_text("RUNNING elapsed=1:00 node=node1\n")
    (state_dir / "sacct.out").write_text("RUNNING\n")
    out = _run("bash", WAIT_JOB, "123", "0", "", "1", env=env)
    assert out.returncode == 3
    assert "state=RUNNING" in out.stdout


def test_wait_job_does_not_treat_a_missing_squeue_entry_as_finished(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.out").write_text("RUNNING\n")  # squeue prints nothing, as on a transient failure
    out = _run("bash", WAIT_JOB, "123", "0", "", "1", env=env)
    assert out.returncode == 3


def test_wait_job_rejects_bad_and_unknown_job_ids(fake_slurm) -> None:
    _, env = fake_slurm
    assert _run("bash", WAIT_JOB, "abc", env=env).returncode == 2
    unknown = _run("bash", WAIT_JOB, "123", "5", env=env)
    assert unknown.returncode == 2
    assert "unknown job id" in unknown.stderr
