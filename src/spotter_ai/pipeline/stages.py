"""The five deterministic stages of the plant-phenotyping pipeline.

Each stage is a pure function over JSON artifact files: it reads its inputs
from disk (if any), computes a result deterministically, writes a JSON
artifact, and returns that artifact's path. Stages do not talk to the
provenance store directly -- :mod:`spotter_ai.pipeline.campaign` wires stage
execution to :class:`spotter_ai.provenance.store.ProvenanceStore` so the
stages themselves stay trivially unit-testable.

Pipeline: ``ingest -> calibrate -> segment -> extract_traits -> predict``.

Domain: each run processes a synthetic batch of :data:`N_PLANTS` plant
sensor scans (canopy pixel count, height, and a pre-normalized greenness
ratio). ``ingest`` draws readings from ``random.Random(seed)``, so a run's
data is fully determined by its seed. ``calibrate`` applies a campaign-level
scale/offset correction (read from ``calibration.json``) to the two
physical-scale channels (``leaf_px``, ``height_mm``); the greenness ratio is
already sensor-normalized and is not calibrated. The noise level, plant
count, and the calibrated/uncalibrated feature mix in the biomass model were
tuned (see ``tests/test_pipeline.py``, ``tests/test_server.py``) so that a
healthy campaign's ``mean_biomass`` varies run-to-run with CV ~1-3%, while a
calibration ``scale_factor`` drift from ``1.02`` to ``1.35`` shifts
``mean_biomass`` by double digits (z well past 5 against a healthy
baseline). :data:`N_PLANTS` was raised from an initial 20 to 60 specifically
because ``mean_leaf_area`` and ``mean_height`` -- unlike ``mean_biomass``,
which is damped by its non-calibrated greenness/intercept terms -- are
undamped means of a single noised channel and so carry a visibly higher
natural CV; at 20 plants that was enough to occasionally push one of those
two metrics' healthy leave-one-out z past 3 in an 11-14 run baseline (a
false positive), since :func:`spotter_ai.server.create_server`'s
``campaign_health`` tool takes the worst z across *all* recorded metrics per
run, not just ``mean_biomass``. Tripling the plant count shrinks every
metric's CV via the same ``1/sqrt(N)`` averaging effect without changing the
noise model itself.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path
from typing import Any

#: Version identifier for this stage implementation, recorded on every
#: stage execution so provenance diffing can flag a code-version change.
TOOL_VERSION = "0.1.0"

#: Number of synthetic plants scanned per run. See the module docstring for
#: why this is 60 rather than a smaller, faster-to-generate number.
N_PLANTS = 60

#: Per-plant, per-run multiplicative noise stdev applied to the physical
#: sensor channels (leaf pixel count, height). This is the dominant source of
#: healthy run-to-run variation.
NOISE_STD = 0.18

#: Per-plant, per-run multiplicative noise stdev applied to the pre-normalized
#: greenness ratio (smaller: the on-sensor ratio is comparatively stable).
GREEN_NOISE_STD = 0.09

#: Conversion constant from calibrated leaf pixel count to leaf area (cm^2).
PIXEL_TO_CM2 = 0.01

#: Fixed linear biomass model weights (grams per unit of each trait).
BIOMASS_WEIGHT_LEAF_AREA = 0.28
BIOMASS_WEIGHT_HEIGHT = 1.3
BIOMASS_WEIGHT_GREENNESS = 50.0
BIOMASS_INTERCEPT = 10.0

#: Default calibration.json content for a fresh campaign data directory.
DEFAULT_CALIBRATION: dict[str, float] = {"scale_factor": 1.02, "offset": 0.5}

#: Sensor channels that calibration.json's scale_factor/offset apply to.
CALIBRATED_FIELDS = ("leaf_px", "height_mm")


def _plant_id(index: int) -> str:
    return f"plant-{index + 1:02d}"


def _plant_baseline(index: int) -> tuple[float, float, float]:
    """Fixed, deterministic per-plant baseline sensor values.

    Args:
        index: Zero-based plant index within a run.

    Returns:
        A ``(leaf_px_baseline, height_mm_baseline, green_ratio_baseline)`` tuple.
    """
    leaf_px = 8000.0 + index * 120.0
    height_mm = 220.0 + index * 4.0
    green_ratio = 0.50 + (index % 5) * 0.01
    return leaf_px, height_mm, green_ratio


def write_json(path: Path, payload: Any) -> None:
    """Write a JSON-serializable payload to disk, creating parent directories.

    Args:
        path: Destination file path.
        payload: JSON-serializable content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> Any:
    """Read and parse a JSON file.

    Args:
        path: File path to read.

    Returns:
        The parsed JSON content.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def ingest(run_id: str, seed: int, run_dir: Path) -> Path:
    """Generate deterministic synthetic sensor readings for a run.

    Draws one reading per plant from ``random.Random(seed)`` in a fixed
    plant order, so the same ``(run_id, seed)`` always produces byte-identical
    output.

    Args:
        run_id: The run this artifact belongs to.
        seed: Seed for the deterministic random number generator.
        run_dir: Directory the ``raw.json`` artifact is written into.

    Returns:
        Path to the written ``raw.json`` artifact.
    """
    rng = random.Random(seed)
    readings = []
    for index in range(N_PLANTS):
        leaf_px_baseline, height_baseline, green_baseline = _plant_baseline(index)
        leaf_px = leaf_px_baseline * rng.gauss(1.0, NOISE_STD)
        height_mm = height_baseline * rng.gauss(1.0, NOISE_STD)
        green_ratio = min(1.0, max(0.0, green_baseline * rng.gauss(1.0, GREEN_NOISE_STD)))
        readings.append(
            {
                "plant_id": _plant_id(index),
                "leaf_px": leaf_px,
                "height_mm": height_mm,
                "green_ratio": green_ratio,
            }
        )

    path = run_dir / "raw.json"
    write_json(path, {"run_id": run_id, "seed": seed, "readings": readings})
    return path


def calibrate(run_id: str, run_dir: Path, raw_path: Path, calibration_path: Path) -> Path:
    """Apply the campaign's scale/offset calibration to the physical channels.

    Args:
        run_id: The run this artifact belongs to.
        run_dir: Directory the ``calibrated.json`` artifact is written into.
        raw_path: Path to the ``raw.json`` artifact produced by :func:`ingest`.
        calibration_path: Path to the campaign's ``calibration.json``.

    Returns:
        Path to the written ``calibrated.json`` artifact.
    """
    raw = read_json(raw_path)
    calibration = read_json(calibration_path)
    scale_factor = float(calibration["scale_factor"])
    offset = float(calibration["offset"])

    calibrated_readings = []
    for reading in raw["readings"]:
        calibrated_readings.append(
            {
                "plant_id": reading["plant_id"],
                "leaf_px": reading["leaf_px"] * scale_factor + offset,
                "height_mm": reading["height_mm"] * scale_factor + offset,
                "green_ratio": reading["green_ratio"],
            }
        )

    path = run_dir / "calibrated.json"
    write_json(
        path,
        {"run_id": run_id, "calibration": calibration, "readings": calibrated_readings},
    )
    return path


def segment(run_id: str, run_dir: Path, calibrated_path: Path) -> Path:
    """Group calibrated readings into one canonical segment per plant.

    Validates that every plant contributed exactly one reading and orders
    the output by plant id, giving downstream stages a clean, schema-checked
    per-plant record. (In a fuller system with multiple scans per plant this
    is where repeated readings would be grouped and reconciled.)

    Args:
        run_id: The run this artifact belongs to.
        run_dir: Directory the ``segments.json`` artifact is written into.
        calibrated_path: Path to the ``calibrated.json`` artifact produced by
            :func:`calibrate`.

    Returns:
        Path to the written ``segments.json`` artifact.

    Raises:
        ValueError: If a plant id is missing or duplicated in the input.
    """
    calibrated = read_json(calibrated_path)
    by_plant: dict[str, dict[str, Any]] = {}
    for reading in calibrated["readings"]:
        plant_id = reading["plant_id"]
        if plant_id in by_plant:
            raise ValueError(f"duplicate reading for {plant_id} in {calibrated_path}")
        by_plant[plant_id] = reading

    expected_ids = {_plant_id(i) for i in range(N_PLANTS)}
    missing = expected_ids - by_plant.keys()
    if missing:
        raise ValueError(f"missing readings for plants: {sorted(missing)}")

    segments = [by_plant[plant_id] for plant_id in sorted(by_plant)]

    path = run_dir / "segments.json"
    write_json(path, {"run_id": run_id, "segments": segments})
    return path


def extract_traits(run_id: str, run_dir: Path, segments_path: Path) -> Path:
    """Derive physical plant traits from each plant's calibrated segment.

    Args:
        run_id: The run this artifact belongs to.
        run_dir: Directory the ``traits.json`` artifact is written into.
        segments_path: Path to the ``segments.json`` artifact produced by
            :func:`segment`.

    Returns:
        Path to the written ``traits.json`` artifact.
    """
    segments = read_json(segments_path)
    traits = []
    for record in segments["segments"]:
        traits.append(
            {
                "plant_id": record["plant_id"],
                "leaf_area_cm2": record["leaf_px"] * PIXEL_TO_CM2,
                "height_cm": record["height_mm"] / 10.0,
                "greenness": record["green_ratio"],
            }
        )

    path = run_dir / "traits.json"
    write_json(path, {"run_id": run_id, "traits": traits})
    return path


def predict(run_id: str, run_dir: Path, traits_path: Path) -> Path:
    """Predict per-plant biomass from traits via a fixed linear model, plus run metrics.

    Args:
        run_id: The run this artifact belongs to.
        run_dir: Directory the ``predictions.json`` artifact is written into.
        traits_path: Path to the ``traits.json`` artifact produced by
            :func:`extract_traits`.

    Returns:
        Path to the written ``predictions.json`` artifact. Its ``"metrics"``
        key holds the run-level ``mean_biomass``, ``mean_leaf_area``, and
        ``mean_height``.
    """
    traits = read_json(traits_path)
    predictions = []
    for record in traits["traits"]:
        biomass_g = (
            BIOMASS_WEIGHT_LEAF_AREA * record["leaf_area_cm2"]
            + BIOMASS_WEIGHT_HEIGHT * record["height_cm"]
            + BIOMASS_WEIGHT_GREENNESS * record["greenness"]
            + BIOMASS_INTERCEPT
        )
        predictions.append({"plant_id": record["plant_id"], "biomass_g": biomass_g})

    metrics = {
        "mean_biomass": statistics.fmean(p["biomass_g"] for p in predictions),
        "mean_leaf_area": statistics.fmean(t["leaf_area_cm2"] for t in traits["traits"]),
        "mean_height": statistics.fmean(t["height_cm"] for t in traits["traits"]),
    }

    path = run_dir / "predictions.json"
    write_json(path, {"run_id": run_id, "predictions": predictions, "metrics": metrics})
    return path
