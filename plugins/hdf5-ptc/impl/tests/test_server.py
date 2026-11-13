"""The hdf5-ptc server: handles, two answer lanes, cost from the index, reductions, subsets."""

from __future__ import annotations

import base64
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import h5netcdf
import h5py
import numpy as np
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from hdf5_ptc.server import mcp

FILL = np.float32(9.999e20)


def _meta(session: str, via: str = "code") -> dict:
    return {"ai.iowarp.clio/caller": {"session": session, "root": session, "via": via}}


@pytest.fixture()
def era5_like(tmp_path: Path) -> Path:
    """A small NetCDF-4 file shaped like an ERA5 pressure-level file."""
    path = tmp_path / "pl.nc"
    rng = np.random.default_rng(3)
    data = rng.random((4, 5, 12, 16), dtype=np.float32) * 300
    data[1, 2, 3, 4] = FILL
    data[2, 0, 7, 9] = -5.0  # the minimum
    with h5netcdf.File(path, "w") as nc:
        nc.dimensions = {"time": 4, "level": 5, "latitude": 12, "longitude": 16}
        nc.create_variable("time", ("time",), data=np.arange(4, dtype=np.int32) * 6).attrs[
            "units"
        ] = "hours since 2024-09-26 00:00:00"
        nc.create_variable("level", ("level",), data=np.array([1000, 850, 500, 250, 100.0]))
        nc.create_variable("latitude", ("latitude",), data=np.linspace(35, 15, 12))
        nc.create_variable("longitude", ("longitude",), data=np.linspace(260, 290, 16))
        var = nc.create_variable(
            "T",
            ("time", "level", "latitude", "longitude"),
            data=data,
            chunks=(1, 5, 12, 16),
            compression="gzip",
            fillvalue=FILL,
        )
        var.attrs["units"] = "K"
        var.attrs["long_name"] = "Temperature"
    return path


def _data(result) -> dict:
    return result.structured_content


async def test_a_script_gets_the_whole_array_and_the_model_a_summary(era5_like: Path) -> None:
    async with Client(mcp) as c:
        opened = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s1")))
        h = opened["handle"]
        args = {"file": h, "path": "/T", "start": [0, 0, 0, 0], "count": [4, 5, 12, 16]}
        summary = await c.call_tool("read", args, meta=_meta("s1", "direct"))
        assert "array" not in _data(summary)
        assert "First 24 of 3,840 values" in summary.content[0].text
        full = _data(await c.call_tool("read", {**args, "values": "array"}, meta=_meta("s1")))
        enc = full["array"]
        got = np.frombuffer(base64.b64decode(enc["data"]), dtype=enc["dtype"]).reshape(enc["shape"])
        with h5py.File(era5_like) as f:
            expected = f["T"][()].astype(np.float32)
        expected[expected == FILL] = np.nan
        np.testing.assert_array_equal(np.isnan(got), np.isnan(expected))
        np.testing.assert_allclose(got[~np.isnan(got)], expected[~np.isnan(expected)])


async def test_a_direct_caller_cannot_take_a_whole_array(era5_like: Path) -> None:
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s2")))[
            "handle"
        ]
        with pytest.raises(ToolError, match="array_values_need_code_caller"):
            await c.call_tool(
                "read", {"file": h, "path": "/T", "values": "array"}, meta=_meta("s2", "direct")
            )


async def test_an_array_over_the_inline_cap_is_refused_with_a_reason(
    era5_like, monkeypatch
) -> None:
    monkeypatch.setenv("HDF5_PTC_INLINE_MAX_BYTES", "1000")
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s3")))[
            "handle"
        ]
        with pytest.raises(ToolError, match="selection_exceeds_inline_cap"):
            await c.call_tool(
                "read", {"file": h, "path": "/T", "values": "array"}, meta=_meta("s3")
            )


async def test_handles_belong_to_the_session_that_opened_them(era5_like: Path, tmp_path) -> None:
    other = tmp_path / "other.h5"
    with h5py.File(other, "w") as f:
        f["x"] = np.arange(3)
    async with Client(mcp) as c:
        a = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("sa")))
        b = _data(await c.call_tool("open_file", {"path": str(other)}, meta=_meta("sa")))
        assert a["handle"] != b["handle"]  # two files open at once
        with pytest.raises(ToolError, match="unknown_handle"):
            await c.call_tool("describe", {"file": a["handle"], "path": "/T"}, meta=_meta("sb"))
        await c.call_tool("close_file", {"file": b["handle"]}, meta=_meta("sa"))
        described = _data(
            await c.call_tool("describe", {"file": a["handle"], "path": "/T"}, meta=_meta("sa"))
        )
        assert [d["name"] for d in described["dimensions"]] == [
            "time",
            "level",
            "latitude",
            "longitude",
        ]
        assert described["meaning"]["units"] == "K"


async def test_selection_cost_matches_the_chunk_index(era5_like: Path) -> None:
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s4")))[
            "handle"
        ]
        price = _data(
            await c.call_tool(
                "selection_cost",
                {"file": h, "path": "/T", "start": [1, 0, 2, 2], "count": [2, 5, 4, 4]},
                meta=_meta("s4"),
            )
        )
    with h5py.File(era5_like) as f:
        dsid = f["T"].id
        expected = sum(dsid.get_chunk_info_by_coord((t, 0, 0, 0)).size for t in (1, 2))
    assert price["chunks_touched"] == 2
    assert price["stored_bytes"] == expected
    assert price["exact"] is True


async def test_reduce_gives_one_row_per_time_with_the_minimum_located(era5_like: Path) -> None:
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s5")))[
            "handle"
        ]
        out = _data(
            await c.call_tool(
                "reduce",
                {"file": h, "path": "/T", "ops": ["min", "argmin", "count"], "over": [1, 2, 3]},
                meta=_meta("s5", "direct"),
            )
        )
    rows = out["rows"]
    assert len(rows) == 4 and rows[2]["time"] == "2024-09-26T12:00:00Z"
    assert rows[2]["min"] == -5.0
    at = rows[2]["argmin"]["at"]
    assert at["level"] == 1000.0 and at["latitude"] == pytest.approx(np.linspace(35, 15, 12)[7])
    assert rows[1]["count"] == 5 * 12 * 16 - 1  # the fill value is not counted


async def test_write_subset_netcdf_keeps_coordinates_and_provenance(era5_like, tmp_path) -> None:
    out = tmp_path / "box.nc"
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s6")))[
            "handle"
        ]
        await c.call_tool(
            "write_subset",
            {
                "file": h,
                "items": [{"path": "/T", "start": [0, 0, 2, 2], "count": [2, 5, 4, 4]}],
                "out_path": str(out),
            },
            meta=_meta("s6"),
        )
    with h5netcdf.File(out, "r") as nc:
        assert nc.variables["T"].shape == (2, 5, 4, 4)
        assert list(nc.variables["latitude"][:]) == list(np.linspace(35, 15, 12)[2:6])
        assert json.loads(nc.variables["T"].attrs["source_selection"])["start"] == [0, 0, 2, 2]
        assert nc.attrs["source"] == "pl.nc"


async def test_write_subset_vtk_writes_a_time_series_with_real_axes(era5_like, tmp_path) -> None:
    out = tmp_path / "t_box"
    async with Client(mcp) as c:
        h = _data(await c.call_tool("open_file", {"path": str(era5_like)}, meta=_meta("s7")))[
            "handle"
        ]
        written = _data(
            await c.call_tool(
                "write_subset",
                {
                    "file": h,
                    "items": [{"path": "/T"}],
                    "out_path": str(out),
                    "format": "vtk",
                    "vertical": {"reference": 1000, "scale": 7},
                },
                meta=_meta("s7"),
            )
        )
    assert written["steps"] == 4 and written["grid"] == [16, 12, 5]
    assert written["bounds"][2] < written["bounds"][3]  # latitude ascending for VTK
    assert written["bounds"][4] == pytest.approx(0.0)  # 1000 hPa at the bottom
    pvd = ET.parse(out / "t_box.pvd").getroot()
    assert len(pvd.find("Collection")) == 4
    ET.parse(out / "t_box_0000.vtr")


async def test_urls_open_only_under_the_configured_range_origin(monkeypatch) -> None:
    async with Client(mcp) as c:
        monkeypatch.delenv("CLIO_SOURCE_RANGE_ORIGIN", raising=False)
        with pytest.raises(ToolError, match="range_origin_unconfigured"):
            await c.call_tool("open_file", {"path": "https://example.org/x.h5"}, meta=_meta("s8"))
        monkeypatch.setenv(
            "CLIO_SOURCE_RANGE_ORIGIN", "http://127.0.0.1:8787/v1/sessions/s8/source-ranges"
        )
        with pytest.raises(ToolError, match="url_not_allowed"):
            await c.call_tool("open_file", {"path": "https://example.org/x.h5"}, meta=_meta("s8"))
