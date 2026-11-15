"""The kernel binding against the real server: ``hdf5.read`` returns the array h5py reads."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from hdf5_ptc.server import mcp

BINDING = Path(__file__).resolve().parents[2] / "ai.iowarp.clio" / "kernel" / "hdf5.py"
META = {"ai.iowarp.clio/caller": {"session": "k1", "root": "k1", "via": "code"}}


def test_the_binding_imports_only_the_standard_library() -> None:
    tree = ast.parse(BINDING.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert name.split(".")[0] in sys.stdlib_module_names, name


async def test_read_returns_the_numpy_array_h5py_reads(tmp_path: Path) -> None:
    path = tmp_path / "x.h5"
    data = np.arange(2 * 3 * 4, dtype=np.float32).reshape(2, 3, 4)
    with h5py.File(path, "w") as f:
        f.create_dataset("v", data=data, chunks=(1, 3, 4))

    async with Client(mcp) as client:

        class Tools:
            async def call(self, name: str, **args):
                assert name.startswith("h5_")
                try:
                    result = await client.call_tool(name[3:], args, meta=META)
                except ToolError as exc:
                    raise KernelToolError(str(exc)) from exc
                return result.structured_content

        class KernelToolError(Exception):
            pass

        namespace = {"tools": Tools(), "ToolError": KernelToolError, "__name__": "hdf5"}
        exec(compile(BINDING.read_text(), str(BINDING), "exec"), namespace)
        hdf5 = namespace["export"]

        f = await hdf5.open(str(path))
        got = await f.read("/v", start=[1, 0, 1], count=[1, 3, 2])
        np.testing.assert_array_equal(got, data[1:2, :, 1:3])
        price = await f.cost("/v", start=[0, 0, 0], count=[2, 3, 4])
        assert price["chunks_touched"] == 2
        with pytest.raises(KernelToolError, match="path_not_found"):
            await f.read("/missing")
        await f.close()
