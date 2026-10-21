#!/usr/bin/env python3
"""Compile one LaTeX entrypoint with a local Tectonic executable."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def render(source: Path, output_dir: Path, *, timeout_seconds: float = 180.0) -> Path:
    """Compile ``source`` and return the generated PDF path."""

    tectonic = shutil.which("tectonic")
    if tectonic is None:
        raise RuntimeError("Tectonic is required but was not found on PATH")
    source = source.expanduser().resolve(strict=True)
    if source.suffix.lower() != ".tex":
        raise ValueError("source must be a .tex file")
    output_dir = output_dir.expanduser().resolve(strict=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            tectonic,
            "--only-cached",
            "--keep-logs",
            "--keep-intermediates",
            "--outdir",
            str(output_dir),
            str(source),
        ],
        cwd=source.parent,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            (completed.stderr or completed.stdout or "Tectonic failed")[-8_192:]
        )
    result = output_dir / f"{source.stem}.pdf"
    if not result.is_file():
        raise RuntimeError("Tectonic completed without producing the expected PDF")
    return result


def main() -> int:
    """Run the command-line compiler."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(render(args.source, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
