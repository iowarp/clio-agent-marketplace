"""Functional tests for the geodesy scripts on synthetic catalogs and series."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

PLUGIN = Path(__file__).resolve().parents[1]


def _load(relative: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, PLUGIN / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog = _load("skills/station-catalogs/scripts/station_catalog.py", "geodesy_station_catalog")
trajectory = _load("skills/gnss-time-series/scripts/fit_trajectory.py", "geodesy_fit_trajectory")


@pytest.fixture()
def messy_catalog(tmp_path: Path) -> Path:
    """Unit labels in a second header row, a duplicated column name, a height that is
    called Longitude, longitudes in [0, 360) and a bad row."""

    path = tmp_path / "stations.csv"
    rows = [
        ["Station", "Latitude", "Longitude", "Longitude", "Note"],
        ["", "(deg)", "(m)", "(deg)", ""],
        ["AAAA", "34.10", "120.5", "241.70", "x"],
        ["BBBB", "35.20", "88.0", "-117.90", "y"],
        ["CCCC", "95.00", "10.0", "-117.00", "bad latitude"],
        ["DDDD", "33.90", "15.2", "242.10", "z"],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    return path


def test_profile_flags_duplicates_header_rows_and_candidates(messy_catalog: Path) -> None:
    report = catalog.profile(messy_catalog)

    assert report["rows"] == 5
    assert report["header_like_rows"] == [2]
    by_ref = {c["ref"]: c for c in report["columns"]}
    assert by_ref["#2"]["duplicate_name"] and by_ref["#3"]["duplicate_name"]
    assert by_ref["#1"]["could_be"][0].startswith("latitude? (1 values outside")
    assert any(role.startswith("longitude in [0, 360)?") for role in by_ref["#3"]["could_be"])


def test_write_uses_the_chosen_columns_and_reports_drops(messy_catalog: Path, tmp_path: Path) -> None:
    before = hashlib.sha256(messy_catalog.read_bytes()).hexdigest()
    out = tmp_path / "normalized.csv"

    with pytest.raises(SystemExit, match="choose one by #index"):
        catalog.main(["write", str(messy_catalog), "--id", "Station", "--lat", "Latitude", "--lon", "Longitude", "-o", str(out)])
    assert catalog.main(
        ["write", str(messy_catalog), "--id", "Station", "--lat", "Latitude", "--lon", "#3",
         "--height", "#2", "--wrap-longitude", "-o", str(out), "--out", str(tmp_path / "r.json")]
    ) == 0

    report = json.loads((tmp_path / "r.json").read_text())
    assert report["written_rows"] == 3
    assert report["dropped"] == {"non-numeric coordinate (header-like or missing)": 1, "latitude out of range": 1}
    assert report["longitudes_wrapped_from_0_360"] == 2
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["id"] for r in rows] == ["AAAA", "BBBB", "DDDD"]
    assert float(rows[0]["longitude"]) == pytest.approx(-118.3)
    assert hashlib.sha256(messy_catalog.read_bytes()).hexdigest() == before


def _series(tmp_path: Path, years: float = 6.0) -> Path:
    rng = np.random.default_rng(7)
    start = date(2010, 1, 1)
    days = int(years * 365.25)
    path = tmp_path / "series.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "east", "north", "up", "sig_e", "sig_n", "sig_u"])
        writer.writerow(["", "(m)", "(m)", "(m)", "(m)", "(m)", "(m)"])  # a unit row to skip
        for d in range(0, days, 1):
            if d % 17 == 5:
                continue  # gaps
            day = start + timedelta(days=d)
            t = trajectory.decimal_year(trajectory.datetime(day.year, day.month, day.day, tzinfo=trajectory.timezone.utc))
            dt = t - 2013.0
            east = 0.020 * dt + 0.002 * np.cos(2 * np.pi * dt) + rng.normal(0, 0.001)
            north = -0.010 * dt + (0.015 if t >= 2012.5 else 0.0) + rng.normal(0, 0.001)
            up = 0.001 * dt + 0.004 * np.sin(2 * np.pi * dt) + rng.normal(0, 0.003)
            if d == 400:
                up += 0.2  # one outlier
            writer.writerow([day.isoformat(), east, north, up, 0.001, 0.001, 0.003])
    return path


def test_trajectory_recovers_rates_offsets_and_seasonal_terms(tmp_path: Path) -> None:
    series = _series(tmp_path)
    out = tmp_path / "fit.json"

    assert trajectory.main(
        [str(series), "--time", "date", "--components", "E=east", "N=north", "U=up",
         "--sigmas", "E=sig_e", "N=sig_n", "U=sig_u", "--offset", "2012-07-02",
         "--scale", "1000", "--units", "mm", "--residuals", str(tmp_path / "res.csv"), "--out", str(out)]
    ) == 0

    fit = json.loads(out.read_text())
    assert fit["rows_skipped_unparsable"] == 1
    east, north, up = (fit["components"][k] for k in ("E", "N", "U"))
    assert east["rate_per_year"]["value"] == pytest.approx(20.0, abs=0.2)
    assert north["rate_per_year"]["value"] == pytest.approx(-10.0, abs=0.2)
    (offset,) = north["offsets"].values()
    assert offset["value"] == pytest.approx(15.0, abs=0.5)
    assert east["annual"]["amplitude"] == pytest.approx(2.0, abs=0.3)
    assert up["annual"]["amplitude"] == pytest.approx(4.0, abs=0.5)
    assert up["n_outliers"] >= 1
    assert east["midas_like_rate_per_year"]["value"] == pytest.approx(20.0, abs=0.5)
    assert any("white noise" in c for c in fit["caveats"])
    assert (tmp_path / "res.csv").read_text().count("\n") > 3 * 2000


def test_short_series_warn_about_seasonal_bias(tmp_path: Path) -> None:
    series = _series(tmp_path, years=1.5)
    out = tmp_path / "fit.json"
    assert trajectory.main([str(series), "--time", "date", "--components", "E=east", "--out", str(out)]) == 0
    caveats = " ".join(json.loads(out.read_text())["caveats"])
    assert "2.5 years" in caveats and "No offset epochs" in caveats
