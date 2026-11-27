"""Tests for ``wait_job.sh``, the bundled helper of the ``hpc-batch-jobs`` skill.

The script runs against fake ``squeue``/``sacct``/``scontrol`` commands put first
on ``PATH``, so no Slurm installation is needed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

WAIT_JOB = Path(__file__).resolve().parents[1] / "skills" / "hpc-batch-jobs" / "scripts" / "wait_job.sh"
NO_ACCOUNTING = "sacct: error: Slurm accounting storage is disabled\n"
FORGOTTEN = "slurm_load_jobs error: Invalid job id specified\n"


def _run(*args: str | Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env, timeout=60)


@pytest.fixture
def fake_slurm(tmp_path: Path):
    """Fake squeue/sacct/scontrol whose answers (stdout ``<tool>.out``, stderr
    ``<tool>.err``) come from files the test writes."""
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("squeue", "sacct", "scontrol"):
        script = bin_dir / tool
        script.write_text(
            f'#!/usr/bin/env bash\ncat "{tmp_path}/{tool}.out" 2>/dev/null\ncat "{tmp_path}/{tool}.err" >&2 2>/dev/null\n'
        )
        script.chmod(0o755)
    env = dict(
        os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}", TMPDIR=str(tmp_path / "tmp")
    )
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


def test_without_accounting_a_finished_job_is_read_from_scontrol(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.err").write_text(NO_ACCOUNTING)
    (state_dir / "scontrol.out").write_text(
        "JobId=123 JobName=x JobState=COMPLETED Reason=None ExitCode=0:0 RunTime=00:10:00 "
        "ReqNodeList=(null) ExcNodeList=(null) NodeList=node1 BatchHost=node1\n"
    )
    out = _run("bash", WAIT_JOB, "123", "5", "", "1", env=env)
    assert out.returncode == 0, out.stderr
    assert "job 123 finished: COMPLETED|0:0|00:10:00|node1" in out.stdout


def test_without_accounting_a_running_job_waits_on_scontrol(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.err").write_text(NO_ACCOUNTING)
    (state_dir / "squeue.out").write_text("RUNNING elapsed=1:00 node=node1\n")
    (state_dir / "scontrol.out").write_text("JobId=123 JobState=RUNNING ExitCode=0:0 RunTime=00:01:00 NodeList=node1\n")
    out = _run("bash", WAIT_JOB, "123", "0", "", "1", env=env)
    assert out.returncode == 3
    assert "state=RUNNING" in out.stdout


def test_without_accounting_a_seen_job_the_controller_forgot_has_ended(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.err").write_text(NO_ACCOUNTING)
    (state_dir / "scontrol.out").write_text("JobId=123 JobState=RUNNING ExitCode=0:0 RunTime=00:01:00 NodeList=node1\n")
    assert _run("bash", WAIT_JOB, "123", "0", "", "1", env=env).returncode == 3
    (state_dir / "scontrol.out").unlink()
    (state_dir / "scontrol.err").write_text(FORGOTTEN)
    out = _run("bash", WAIT_JOB, "123", "5", "", "1", env=env)
    assert out.returncode == 4, out.stderr
    assert "how it ended is unknown" in out.stdout


def test_without_accounting_an_unseen_forgotten_id_is_unknown(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.err").write_text(NO_ACCOUNTING)
    (state_dir / "scontrol.err").write_text(FORGOTTEN)
    out = _run("bash", WAIT_JOB, "123", "5", "", "1", env=env)
    assert out.returncode == 2
    assert "keeps no Slurm accounting" in out.stderr


def test_a_controller_that_cannot_be_reached_does_not_end_the_wait(fake_slurm) -> None:
    state_dir, env = fake_slurm
    (state_dir / "sacct.err").write_text(NO_ACCOUNTING)
    (state_dir / "squeue.out").write_text("RUNNING elapsed=1:00 node=node1\n")
    (state_dir / "scontrol.err").write_text("slurm_load_jobs error: Unable to contact slurm controller\n")
    out = _run("bash", WAIT_JOB, "123", "0", "", "1", env=env)
    assert out.returncode == 3