"""Functional tests for the Office/OpenDocument package preservation guard."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path
from types import ModuleType

import pytest


def _guard() -> ModuleType:
    path = (
        Path(__file__).parents[1]
        / "skills"
        / "inspect-office-package"
        / "scripts"
        / "package_guard.py"
    )
    spec = importlib.util.spec_from_file_location("document_package_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load package guard")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package(path: Path, *, document: str, extension: str = "preserve") -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
        archive.writestr("customXml/item1.xml", extension)


def test_compare_allows_owned_part_but_rejects_unknown_part_loss(
    tmp_path: Path,
) -> None:
    guard = _guard()
    before_path = tmp_path / "before.docx"
    after_path = tmp_path / "after.docx"
    _package(before_path, document="<p>before</p>")
    _package(after_path, document="<p>after</p>")
    before = guard.inventory(before_path)

    allowed = guard.compare(before, guard.inventory(after_path), ["word/document.xml"])
    assert allowed["ok"] is True

    with zipfile.ZipFile(after_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<p>after</p>")
    blocked = guard.compare(before, guard.inventory(after_path), ["word/document.xml"])
    assert blocked["ok"] is False
    assert blocked["unexpected"] == ["customXml/item1.xml"]


def test_inventory_rejects_archive_traversal(tmp_path: Path) -> None:
    guard = _guard()
    unsafe = tmp_path / "unsafe.docx"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../escape.xml", "<x/>")

    with pytest.raises(ValueError, match="unsafe package path"):
        guard.inventory(unsafe)
