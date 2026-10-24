"""Functional tests for convert-scientific-data's convert_to_parquet.py.

Everything here is synthetic: small HDF5 files (and ADIOS2 BP5 output when the
adios2 package is importable) carrying every dtype case the skill's map names.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

h5py = pytest.importorskip("h5py")

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "skills" / "convert-scientific-data" / "scripts" / "convert_to_parquet.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("clio_data_convert", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["clio_data_convert"] = module
    spec.loader.exec_module(module)
    return module


convert = _load()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(*argv: str) -> int:
    return convert.main(list(argv))


@pytest.fixture()
def table_h5(tmp_path: Path) -> Path:
    """A flat table: one dataset per column, with NaN, uint64 overflow and strings."""

    path = tmp_path / "source.h5"
    n = 6
    with h5py.File(path, "w") as f:
        f.attrs["title"] = "synthetic"
        g = f.create_group("obs")
        temp = g.create_dataset("temp", data=np.array([1.5, np.nan, 3.0, 4.25, np.nan, 6.0]))
        temp.attrs["units"] = "K"
        g.create_dataset("count", data=np.arange(n, dtype="int32"))
        g.create_dataset("big", data=np.array([2**63 + 5, 0, 1, 2, 3, 2**64 - 1], dtype="uint64"))
        g.create_dataset(
            "half", data=np.array([0.5, 1.0, np.nan, 2.0, -1.0, 65504.0], dtype="float16")
        )
        g.create_dataset("flag", data=np.array([True, False] * 3))
        g.create_dataset("label", data=np.array([b"a", b"bb", b"", b"ccc", b"d", b"e"], dtype="S3"))
        g.create_dataset(
            "name",
            data=["α", "beta", "γ", "", "e", "f"],
            dtype=h5py.string_dtype("utf-8"),
        )
        kind = h5py.enum_dtype({"LOW": 0, "HIGH": 7}, basetype="i1")
        g.create_dataset("level", data=np.array([0, 7, 7, 0, 0, 7], dtype="i1"), dtype=kind)
        g.create_dataset("wave", data=np.arange(n, dtype="complex64") * (1 + 2j))
        g.create_dataset("ref", data=[f.ref] * n, dtype=h5py.ref_dtype)
        g.create_dataset("scalar", data=42)
    return path


def test_flat_table_converts_and_verifies(table_h5: Path, tmp_path: Path) -> None:
    before = _sha(table_h5)
    out = tmp_path / "out" / "table.parquet"
    report_path = tmp_path / "report.json"

    assert (
        _run("hdf5", str(table_h5), "--group", "/obs", "-o", str(out), "--report", str(report_path))
        == 0
    )

    assert _sha(table_h5) == before, "the source is never written"
    report = json.loads(report_path.read_text())
    assert report["ok"] and report["rows"] == 6
    columns = {c["name"]: c for c in report["columns"]}
    assert columns["temp"]["nan_source"] == columns["temp"]["nan_parquet"] == 2
    assert columns["half"]["action"] == "widen" and columns["half"]["nan_parquet"] == 1
    assert columns["level"]["action"] == "enum->dictionary"
    assert all(c["sha256_expected"] == c["sha256_parquet"] for c in report["columns"])
    skipped = {s["source"]: s["reason"] for s in report["skipped"]}
    assert "complex" in skipped["/obs/wave"] and "--complex split" in skipped["/obs/wave"]
    assert "references" in skipped["/obs/ref"]
    assert "scalar" in skipped["/obs/scalar"]

    table = pq.read_table(out)
    assert table.schema.field("big").type == pa.uint64()
    assert table.column("big").to_pylist()[0] == 2**63 + 5
    assert table.schema.field("half").type == pa.float32()
    assert table.column("half").to_pylist()[5] == 65504.0
    assert table.column("label").to_pylist() == ["a", "bb", "", "ccc", "d", "e"]
    assert table.column("name").to_pylist()[0] == "α"
    assert table.column("level").to_pylist() == ["LOW", "HIGH", "HIGH", "LOW", "LOW", "HIGH"]
    assert table.schema.field("temp").metadata[b"source"] == b"/obs/temp"
    assert json.loads(table.schema.field("temp").metadata[b"attributes"]) == {"units": "K"}
    provenance = json.loads(table.schema.metadata[convert.METADATA_KEY])
    assert provenance["source_sha256"] == before
    assert provenance["file"]["scalars"] == {"/obs/scalar": 42}
    assert {s["source"] for s in provenance["skipped"]} == {"/obs/wave", "/obs/ref", "/obs/scalar"}


def test_batching_does_not_change_the_checksums(table_h5: Path, tmp_path: Path) -> None:
    one, two = tmp_path / "a.json", tmp_path / "b.json"
    assert (
        _run(
            "hdf5",
            str(table_h5),
            "--group",
            "/obs",
            "-o",
            str(tmp_path / "a.parquet"),
            "--report",
            str(one),
        )
        == 0
    )
    assert (
        _run(
            "hdf5",
            str(table_h5),
            "--group",
            "/obs",
            "-o",
            str(tmp_path / "b.parquet"),
            "--report",
            str(two),
            "--batch-rows",
            "4",
        )
        == 0
    )
    sums = [
        {c["name"]: c["sha256_parquet"] for c in json.loads(p.read_text())["columns"]}
        for p in (one, two)
    ]
    assert sums[0] == sums[1]


def test_complex_split_is_opt_in(table_h5: Path, tmp_path: Path) -> None:
    out = tmp_path / "c.parquet"
    assert (
        _run(
            "hdf5",
            str(table_h5),
            "--datasets",
            "/obs/wave",
            "/obs/count",
            "-o",
            str(out),
            "--complex",
            "split",
        )
        == 0
    )
    wave = pq.read_table(out).column("wave").to_pylist()
    assert wave[2] == {"real": 2.0, "imag": 4.0}


def test_compound_nested_and_multidimensional(tmp_path: Path) -> None:
    path = tmp_path / "compound.h5"
    inner = np.dtype([("x", "f8"), ("y", "f8")])
    record = np.dtype(
        [("id", "i4"), ("pos", inner), ("spec", "f4", (3,)), ("note", h5py.string_dtype())]
    )
    data = np.zeros(4, dtype=record)
    data["id"] = [1, 2, 3, 4]
    data["pos"]["x"] = [0.1, 0.2, np.nan, 0.4]
    data["spec"] = np.arange(12, dtype="f4").reshape(4, 3)
    data["note"] = ["a", "b", "c", "d"]
    with h5py.File(path, "w") as f:
        f.create_dataset("records", data=data)
        f.create_dataset("grid", data=np.arange(8.0).reshape(4, 2))
    out = tmp_path / "compound.parquet"
    report = tmp_path / "r.json"

    assert (
        _run(
            "hdf5",
            str(path),
            "--datasets",
            "/records",
            "/grid",
            "-o",
            str(out),
            "--report",
            str(report),
        )
        == 0
    )

    table = pq.read_table(out)
    assert table.column_names == [
        "records.id",
        "records.pos",
        "records.spec",
        "records.note",
        "grid",
    ]
    assert table.schema.field("records.pos").type == pa.struct(
        [("x", pa.float64()), ("y", pa.float64())]
    )
    assert table.schema.field("records.spec").type == pa.list_(pa.float32(), 3)
    assert table.column("records.spec").to_pylist()[1] == [3.0, 4.0, 5.0]
    assert table.column("grid").to_pylist()[3] == [6.0, 7.0]
    pos = next(c for c in json.loads(report.read_text())["columns"] if c["name"] == "records.pos")
    assert pos["nan_source"] == pos["nan_parquet"] == 1


def test_cf_time_and_fill_values_change_only_on_request(tmp_path: Path) -> None:
    path = tmp_path / "cf.h5"
    with h5py.File(path, "w") as f:
        t = f.create_dataset("time", data=np.array([0.0, 0.5, 1.0]))
        t.attrs["units"] = "days since 2000-01-01 00:00:00"
        t.attrs["calendar"] = "standard"
        v = f.create_dataset("value", data=np.array([1.0, -9999.0, 3.0]))
        v.attrs["_FillValue"] = np.float64(-9999.0)
    kept = tmp_path / "kept.parquet"
    assert _run("hdf5", str(path), "--datasets", "/time", "/value", "-o", str(kept)) == 0
    table = pq.read_table(kept)
    assert table.column("time").to_pylist() == [0.0, 0.5, 1.0]
    assert table.column("value").null_count == 0

    decoded = tmp_path / "decoded.parquet"
    report = tmp_path / "r.json"
    assert (
        _run(
            "hdf5",
            str(path),
            "--datasets",
            "/time",
            "/value",
            "-o",
            str(decoded),
            "--cf-time",
            "decode",
            "--mask-fill",
            "--report",
            str(report),
        )
        == 0
    )
    table = pq.read_table(decoded)
    assert table.schema.field("time").type == pa.timestamp("us", tz="UTC")
    stamps = [s.isoformat() for s in table.column("time").to_pylist()]
    assert stamps == [
        "2000-01-01T00:00:00+00:00",
        "2000-01-01T12:00:00+00:00",
        "2000-01-02T00:00:00+00:00",
    ]
    assert table.column("value").to_pylist() == [1.0, None, 3.0]
    value = next(c for c in json.loads(report.read_text())["columns"] if c["name"] == "value")
    assert value["masked_to_null"] == 1 and value["checksum_basis"] == "converted values"


@pytest.mark.parametrize(
    "case",
    ["calendar", "lengths", "utf8", "exists"],
)
def test_refusals_write_nothing(
    tmp_path: Path, case: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.h5"
    out = tmp_path / "bad.parquet"
    with h5py.File(path, "w") as f:
        t = f.create_dataset("t", data=np.arange(3.0))
        t.attrs["units"] = "days since 2000-01-01"
        t.attrs["calendar"] = "noleap"
        f.create_dataset("short", data=np.arange(2))
        # Bytes that are not UTF-8 in a dataset declared UTF-8 (low-level API: h5py's
        # high-level writer would refuse to produce it).
        utf8 = h5py.h5t.C_S1.copy()
        utf8.set_size(2)
        utf8.set_cset(h5py.h5t.CSET_UTF8)
        dsid = h5py.h5d.create(f.id, b"text", utf8, h5py.h5s.create_simple((3,)))
        dsid.write(
            h5py.h5s.ALL, h5py.h5s.ALL, np.array([b"ok", b"\xff\xfe", b"x"], dtype="S2"), mtype=utf8
        )
    if case == "calendar":
        argv = ["--datasets", "/t", "--cf-time", "decode"]
    elif case == "lengths":
        argv = ["--datasets", "/t", "/short"]
    elif case == "utf8":
        argv = ["--datasets", "/text"]
    else:
        out.write_bytes(b"keep")
        argv = ["--datasets", "/t"]

    assert _run("hdf5", str(path), *argv, "-o", str(out)) == 2

    assert "not converted" in capsys.readouterr().err
    assert (out.read_bytes() == b"keep") if case == "exists" else not out.exists()
    assert not out.with_name(out.name + ".partial").exists()


def test_column_hash_separates_nulls_nan_and_sentinels() -> None:
    def digest(array: pa.Array) -> str:
        h = convert.ColumnHash()
        h.update(array)
        return h.hexdigest()

    base = digest(pa.array([1.0, None, 3.0]))
    assert base != digest(pa.array([1.0, float("nan"), 3.0]))
    assert base != digest(pa.array([1.0, 0.0, 3.0]))
    assert digest(pa.array([1, 2], pa.int32())) == digest(pa.array([1, 2], pa.int64()))
    whole = convert.ColumnHash()
    whole.update(pa.chunked_array([[1.0, None], [3.0]]))
    assert whole.hexdigest() == base


def test_adios2_steps_become_rows(tmp_path: Path) -> None:
    adios2 = pytest.importorskip("adios2")
    if not hasattr(adios2, "Stream"):
        pytest.skip("needs the adios2 2.10+ Python API")
    values, arrays = tmp_path / "values.bp", tmp_path / "arrays.bp"
    with adios2.Stream(str(values), "w") as s:
        for _ in s.steps(3):
            step = s.current_step()
            s.write("energy", float(step) * 1.5)
            s.write("iteration", int(step))
    with adios2.Stream(str(arrays), "w") as s:
        for _ in s.steps(2):
            step = s.current_step()
            s.write("T", np.arange(4, dtype="f8") + step, [4], [0], [4])
            if step == 0:
                s.write_attribute("units", "K", "T")
    out = tmp_path / "values.parquet"
    assert _run("adios", str(values), "--variables", "energy", "iteration", "-o", str(out)) == 0
    table = pq.read_table(out)
    assert table.column("energy").to_pylist() == [0.0, 1.5, 3.0]
    assert table.column("step").to_pylist() == [0, 1, 2]

    out = tmp_path / "arrays.parquet"
    assert _run("adios", str(arrays), "--variables", "T", "-o", str(out)) == 0
    table = pq.read_table(out)
    assert table.num_rows == 8
    assert table.column("T").to_pylist()[4:] == [1.0, 2.0, 3.0, 4.0]
    assert table.column("step").to_pylist() == [0] * 4 + [1] * 4
    assert json.loads(table.schema.field("T").metadata[b"attributes"]) == {"units": "K"}


def test_a_corrupted_write_fails_verification(
    table_h5: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read-back compares against the source, so a value changed on the way out is caught."""

    class Corrupting(pq.ParquetWriter):
        def write_batch(self, batch: pa.RecordBatch, row_group_size: int | None = None) -> None:
            index = batch.schema.get_field_index("count")
            values = batch.column(index).to_pylist()
            values[0] += 1
            columns = list(batch.columns)
            columns[index] = pa.array(values, batch.schema.field(index).type)
            super().write_batch(
                pa.RecordBatch.from_arrays(columns, schema=batch.schema), row_group_size
            )

    monkeypatch.setattr(convert.pq, "ParquetWriter", Corrupting)
    report = tmp_path / "r.json"

    assert (
        _run(
            "hdf5",
            str(table_h5),
            "--group",
            "/obs",
            "-o",
            str(tmp_path / "x.parquet"),
            "--report",
            str(report),
        )
        == 1
    )

    bad = [c["name"] for c in json.loads(report.read_text())["columns"] if not c["ok"]]
    assert bad == ["count"]
