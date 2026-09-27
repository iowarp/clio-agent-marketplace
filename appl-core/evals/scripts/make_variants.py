# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15"]
# ///
# pyright: reportAttributeAccessIssue=false
# (pyarrow.compute functions are generated at import time; there are no stubs.)
"""Make a mutated copy of an export bundle for held-out onboarding tests.

Copies the bundle's tables (Parquet/CSV/TSV/JSON), manifest, and docs into
OUT_DIR, WITHOUT the heavy asset directories (images, masks, geometry,
viewer files) and without any ``.clio`` agent artefacts, then applies one
mutation:

* ``categorical_treatment``: numeric treatment/dose columns become labels
  (lowest level -> ``--control-label``, others -> ``--treated-label``).
* ``unbalanced``: a seeded random subset of units is removed from every table.
* ``drop_modality``: one modality is removed from the manifest, its
  directory and doc are not copied, and rows naming it are removed.
* ``rename_columns``: some columns are renamed consistently in tables,
  column catalogs, the manifest, and docs.
* ``export_v7``: ``export_version`` becomes 7 (and one column is renamed);
  an agent built for version 6 must refuse this bundle.
* ``sentinel_elsewhere``: the float64 maximum is injected into a float column
  of a different table than any that already holds such values.

Declared row counts in the manifest are updated to match mutated tables, so
the only new inconsistency is the intended one. What was done is written to
``OUT_DIR.variant.json`` (next to, not inside, the bundle, so an agent under
test does not see it).

The source bundle is never written to: every write is checked to be outside
it. Do not point OUT_DIR inside the source.

Usage::

    python make_variants.py SRC_BUNDLE OUT_DIR --variant NAME [--seed 0] [--force] [--link-assets]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

VARIANTS = (
    "categorical_treatment",
    "unbalanced",
    "drop_modality",
    "rename_columns",
    "export_v7",
    "sentinel_elsewhere",
)
TABLE_SUFFIXES = frozenset({".parquet", ".pq", ".csv", ".tsv"})
COPY_SUFFIXES = TABLE_SUFFIXES | {".json", ".md", ".yaml", ".yml", ".txt"}
DOC_SUFFIXES = frozenset({".md", ".yaml", ".yml", ".txt"})
TREATMENT_RE = re.compile(
    r"(^|_)(treatment|dose|spike|concentration)(_\d+)?$", re.IGNORECASE
)
KEYLIKE_RE = re.compile(
    r"(^|_)(id|key|keys|time|timestamp|date|datetime|round|plant|unit|experiment|modality|path|name)(_|$)",
    re.IGNORECASE,
)
UNIT_COLUMNS = ("plant_id", "unit_id", "plant", "pot_id", "sample_id")
MODALITY_COLUMNS = ("modality", "modality_id", "sensor", "sensor_id")
MODALITY_ID_KEYS = ("modality_id", "id", "name", "modality")
CATALOG_NAME_COLUMNS = ("column", "column_name", "name", "variable")
FLOAT64_MAX = 1.7976931348623157e308
HUGE = 1e300
#: A directory with at least this many files, of which under 10% are tables or
#: docs, is an asset directory and is not copied.
ASSET_DIR_MIN_FILES = 50


class VariantError(RuntimeError):
    """A variant cannot be produced from this bundle."""


def _inventory_module() -> ModuleType:
    """Import onboard-dataset's inventory.py for its manifest-count pairing."""

    path = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "onboard-dataset"
        / "scripts"
        / "inventory.py"
    )
    spec = importlib.util.spec_from_file_location("appl_core_inventory", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bundle:
    """The output copy, with guarded writes."""

    def __init__(self, src: Path, out: Path) -> None:
        self.src = src.resolve()
        self.out = out.resolve()
        self.mutations: list[dict[str, Any]] = []

    def guard(self, path: Path) -> Path:
        """Refuse any write that would land inside the source bundle."""

        resolved = path.resolve()
        if resolved == self.src or self.src in resolved.parents:
            raise VariantError(
                f"refusing to write inside the source bundle: {resolved}"
            )
        if not (resolved == self.out or self.out in resolved.parents):
            raise VariantError(
                f"refusing to write outside the output bundle: {resolved}"
            )
        return resolved

    def tables(self) -> list[Path]:
        return sorted(
            p
            for p in self.out.rglob("*")
            if p.is_file() and p.suffix.lower() in TABLE_SUFFIXES
        )

    def manifest_path(self) -> Path | None:
        path = self.out / "manifest.json"
        return path if path.is_file() else None

    def load_manifest(self) -> Any:
        path = self.manifest_path()
        return json.loads(path.read_text(encoding="utf-8")) if path else None

    def save_manifest(self, manifest: Any) -> None:
        path = self.manifest_path()
        if path is None:
            return
        self.guard(path).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )


# ---------------------------------------------------------------- tables


def read_any(path: Path) -> pa.Table:
    """Read one Parquet/CSV/TSV table."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pq.read_table(path)
    return pacsv.read_csv(
        path,
        parse_options=pacsv.ParseOptions(delimiter="\t" if suffix == ".tsv" else ","),
    )


def _csv_safe(table: pa.Table) -> pa.Table:
    """Render nested columns as Python-style strings so CSV can hold them."""

    columns = []
    for field, column in zip(table.schema, table.columns):
        if pa.types.is_nested(field.type):
            values = [None if v is None else repr(v) for v in column.to_pylist()]
            columns.append(pa.array(values, type=pa.string()))
        else:
            columns.append(column)
    return pa.Table.from_arrays(columns, names=table.column_names)


def write_any(bundle: Bundle, table: pa.Table, path: Path) -> None:
    """Write one table in the format its suffix names (guarded)."""

    target = bundle.guard(path)
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        pq.write_table(table, target)
    else:
        options = pacsv.WriteOptions(delimiter="\t" if suffix == ".tsv" else ",")
        pacsv.write_csv(_csv_safe(table), target, write_options=options)


def transform_tables(
    bundle: Bundle, fn: Callable[[pa.Table, Path], pa.Table | None]
) -> dict[str, int]:
    """Apply ``fn`` to every table; CSV twins of changed Parquet files are
    regenerated from the changed Parquet. Returns new row counts by relative path."""

    changed: dict[str, int] = {}
    mutated_parquet: dict[Path, pa.Table] = {}
    tables = bundle.tables()
    for path in (p for p in tables if p.suffix.lower() in {".parquet", ".pq"}):
        new = fn(read_any(path), path)
        if new is not None:
            write_any(bundle, new, path)
            mutated_parquet[path.with_suffix("")] = new
            changed[path.relative_to(bundle.out).as_posix()] = new.num_rows
    for path in (p for p in tables if p.suffix.lower() in {".csv", ".tsv"}):
        twin = mutated_parquet.get(path.with_suffix(""))
        parquet_twin_exists = any(
            path.with_suffix(s).is_file() for s in (".parquet", ".pq")
        )
        if twin is not None:
            new: pa.Table | None = twin
        elif parquet_twin_exists:
            continue
        else:
            new = fn(read_any(path), path)
        if new is not None:
            write_any(bundle, new, path)
            changed[path.relative_to(bundle.out).as_posix()] = new.num_rows
    return changed


def _set_pointer(document: Any, pointer: str, value: Any) -> None:
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    node = document
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def sync_manifest_counts(bundle: Bundle, changed: dict[str, int]) -> None:
    """Update the manifest's declared counts for tables whose rows changed."""

    manifest = bundle.load_manifest()
    if manifest is None or not changed:
        return
    inventory = _inventory_module()
    touched = False
    for declared in inventory.declared_table_counts(manifest):
        rel = inventory.norm_rel(declared["path"])
        if rel in changed and declared["declared_rows"] != changed[rel]:
            _set_pointer(manifest, declared["pointer"], changed[rel])
            touched = True
    if touched:
        bundle.save_manifest(manifest)


# ---------------------------------------------------------------- copying


def _asset_dirs_from_manifest(manifest: Any) -> set[str]:
    dirs: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if "asset" in str(key).lower():
                    for item in (
                        value
                        if isinstance(value, list)
                        else value.values()
                        if isinstance(value, dict)
                        else [value]
                    ):
                        if isinstance(item, str) and Path(item).suffix == "":
                            dirs.add(item.replace("\\", "/").strip("/"))
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(manifest)
    return dirs


def _is_asset_dir(directory: Path) -> bool:
    files = [p for p in directory.iterdir() if p.is_file()]
    if len(files) < ASSET_DIR_MIN_FILES:
        return False
    data = sum(
        1
        for p in files
        if p.suffix.lower() in TABLE_SUFFIXES | DOC_SUFFIXES | {".json"}
    )
    return data / len(files) < 0.1


def copy_bundle(bundle: Bundle, *, link_assets: bool) -> dict[str, Any]:
    """Copy tables, manifest, and docs; skip assets and agent artefacts."""

    src = bundle.src
    manifest_path = src / "manifest.json"
    declared_assets: set[str] = set()
    if manifest_path.is_file():
        try:
            declared_assets = _asset_dirs_from_manifest(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            declared_assets = set()
    skipped: list[str] = []
    linked: list[str] = []
    copied = 0
    for dirpath, dirnames, filenames in os.walk(src):
        current = Path(dirpath)
        rel_dir = current.relative_to(src).as_posix()
        keep = []
        for name in sorted(dirnames):
            child = current / name
            rel = (Path(rel_dir) / name).as_posix() if rel_dir != "." else name
            if name.startswith("."):
                continue
            if rel in declared_assets or _is_asset_dir(child):
                skipped.append(rel)
                if link_assets:
                    target = bundle.guard(bundle.out / rel)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        os.symlink(child, target, target_is_directory=True)
                        linked.append(rel)
                    except OSError:
                        pass
                continue
            keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            source = current / name
            if name.startswith(".") or source.suffix.lower() not in COPY_SUFFIXES:
                continue
            if (
                source.suffix.lower() == ".txt"
                and rel_dir not in (".", "docs")
                and not rel_dir.startswith("docs/")
            ):
                continue  # headerless geometry text files are assets
            target = bundle.guard(bundle.out / source.relative_to(src))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
    return {
        "copied_files": copied,
        "skipped_asset_dirs": sorted(skipped),
        "linked_asset_dirs": linked,
    }


# ---------------------------------------------------------------- variants


def _numeric_values(column: pa.ChunkedArray) -> list[float | None] | None:
    values: list[float | None] = []
    for value in column.to_pylist():
        if value is None or (isinstance(value, str) and not value.strip()):
            values.append(None)
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return None
    return values


def categorical_treatment(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    wanted = set(args.columns.split(",")) if args.columns else None
    seen: dict[str, list[str]] = {}
    levels: set[float] = set()
    for path in bundle.tables():
        table = read_any(path)
        for name in table.column_names:
            if (wanted is None and TREATMENT_RE.search(name)) or (
                wanted and name in wanted
            ):
                values = _numeric_values(table.column(name))
                if values is not None:
                    levels.update(v for v in values if v is not None)
    if not levels:
        raise VariantError("no numeric treatment/dose columns found; pass --columns")
    control = min(levels)

    def label(value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return args.control_label if float(value) == control else args.treated_label

    def fn(table: pa.Table, path: Path) -> pa.Table | None:
        changed = False
        for index, name in enumerate(table.column_names):
            if not (
                (wanted is None and TREATMENT_RE.search(name))
                or (wanted and name in wanted)
            ):
                continue
            if _numeric_values(table.column(name)) is None:
                continue
            labels = pa.array(
                [label(v) for v in table.column(name).to_pylist()], type=pa.string()
            )
            table = table.set_column(index, pa.field(name, pa.string()), labels)
            seen.setdefault(path.relative_to(bundle.out).as_posix(), []).append(name)
            changed = True
        return table if changed else None

    changed = transform_tables(bundle, fn)
    sync_manifest_counts(bundle, changed)
    return {
        "control_level": control,
        "control_label": args.control_label,
        "treated_label": args.treated_label,
        "columns": seen,
    }


def _column_names(path: Path) -> list[str]:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return list(pq.read_schema(path).names)
    return read_any(path).column_names


def unbalanced(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    tables = bundle.tables()
    column = args.unit_column
    if column is None:
        for path in tables:
            column = next((c for c in UNIT_COLUMNS if c in _column_names(path)), None)
            if column:
                break
    units: set[str] = set()
    for path in tables:
        if column and column in _column_names(path):
            values = read_any(path).column(column).to_pylist()
            units.update(str(v) for v in values if v is not None)
    if not column or not units:
        raise VariantError("no unit column found; pass --unit-column")
    ordered = sorted(units)
    count = max(1, round(len(ordered) * args.drop_fraction))
    dropped = set(rng.sample(ordered, count))

    def fn(table: pa.Table, path: Path) -> pa.Table | None:
        if column not in table.column_names:
            return None
        keep = pa.array(
            [
                v is None or str(v) not in dropped
                for v in table.column(column).to_pylist()
            ]
        )
        return table.filter(keep)

    changed = transform_tables(bundle, fn)
    sync_manifest_counts(bundle, changed)
    return {
        "unit_column": column,
        "dropped_units": sorted(dropped),
        "units_before": len(ordered),
    }


def _modality_entries(manifest: Any) -> list[tuple[list[Any], int, str]]:
    found = []
    if isinstance(manifest, dict):
        modalities = manifest.get("modalities")
        if isinstance(modalities, list):
            for index, entry in enumerate(modalities):
                if isinstance(entry, dict):
                    ident = next(
                        (
                            entry[k]
                            for k in MODALITY_ID_KEYS
                            if isinstance(entry.get(k), str)
                        ),
                        None,
                    )
                    if ident:
                        found.append((modalities, index, ident))
    return found


def drop_modality(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    manifest = bundle.load_manifest()
    entries = _modality_entries(manifest)
    if not entries:
        raise VariantError(
            "the manifest has no 'modalities' list with identifiable entries"
        )
    if args.modality:
        match = [e for e in entries if e[2].lower() == args.modality.lower()]
        if not match:
            raise VariantError(
                f"modality {args.modality!r} not in manifest: {[e[2] for e in entries]}"
            )
        chosen = match[0]
    else:
        chosen = rng.choice(entries)
    modalities, index, ident = chosen
    del modalities[index]
    bundle.save_manifest(manifest)
    removed: list[str] = []
    for path in sorted(bundle.out.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.name.lower() == ident.lower() and path.is_dir():
            shutil.rmtree(bundle.guard(path))
            removed.append(path.relative_to(bundle.out).as_posix())
        elif (
            path.is_file()
            and path.suffix.lower() in DOC_SUFFIXES
            and path.stem.lower() == ident.lower()
        ):
            bundle.guard(path).unlink()
            removed.append(path.relative_to(bundle.out).as_posix())

    def fn(table: pa.Table, path: Path) -> pa.Table | None:
        column = next((c for c in MODALITY_COLUMNS if c in table.column_names), None)
        if column is None:
            return None
        keep = pa.array(
            [
                v is None or str(v).lower() != ident.lower()
                for v in table.column(column).to_pylist()
            ]
        )
        filtered = table.filter(keep)
        return filtered if filtered.num_rows != table.num_rows else None

    changed = transform_tables(bundle, fn)
    sync_manifest_counts(bundle, changed)
    return {
        "modality": ident,
        "removed_paths": removed,
        "tables_filtered": sorted(changed),
    }


def _pick_renames(bundle: Bundle, count: int, rng: random.Random) -> dict[str, str]:
    names: set[str] = set()
    for path in bundle.tables():
        if path.suffix.lower() in {".parquet", ".pq"}:
            names.update(pq.read_schema(path).names)
    candidates = sorted(n for n in names if not KEYLIKE_RE.search(n))
    if not candidates:
        raise VariantError("no renameable (non-key) columns found")
    return {
        old: f"alt_{old}" for old in rng.sample(candidates, min(count, len(candidates)))
    }


def _replace_json_strings(node: Any, mapping: dict[str, str]) -> Any:
    if isinstance(node, dict):
        return {
            mapping.get(k, k) if isinstance(k, str) else k: _replace_json_strings(
                v, mapping
            )
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_replace_json_strings(v, mapping) for v in node]
    if isinstance(node, str):
        return mapping.get(node, node)
    return node


def apply_renames(bundle: Bundle, mapping: dict[str, str]) -> dict[str, Any]:
    touched: list[str] = []

    def fn(table: pa.Table, path: Path) -> pa.Table | None:
        new_names = [mapping.get(n, n) for n in table.column_names]
        changed = new_names != table.column_names
        table = table.rename_columns(new_names)
        for index, name in enumerate(table.column_names):
            field = table.schema.field(index)
            if name in CATALOG_NAME_COLUMNS and pa.types.is_string(field.type):
                values = table.column(index).to_pylist()
                if any(v in mapping for v in values):
                    table = table.set_column(
                        index,
                        field,
                        pa.array([mapping.get(v, v) for v in values], type=pa.string()),
                    )
                    changed = True
        if changed:
            touched.append(path.relative_to(bundle.out).as_posix())
        return table if changed else None

    transform_tables(bundle, fn)
    for path in sorted(bundle.out.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            new = _replace_json_strings(data, mapping)
            if new != data:
                bundle.guard(path).write_text(
                    json.dumps(new, indent=2) + "\n", encoding="utf-8"
                )
                touched.append(path.relative_to(bundle.out).as_posix())
        elif suffix in {".md", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            new_text = text
            for old, new_name in mapping.items():
                new_text = re.sub(
                    rf"(?<![\w]){re.escape(old)}(?![\w])", new_name, new_text
                )
            if new_text != text:
                bundle.guard(path).write_text(new_text, encoding="utf-8")
                touched.append(path.relative_to(bundle.out).as_posix())
    return {"renames": mapping, "files_touched": sorted(set(touched))}


def rename_columns(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    if args.rename:
        mapping = dict(item.split("=", 1) for item in args.rename)
    else:
        mapping = _pick_renames(bundle, args.count, rng)
    return apply_renames(bundle, mapping)


def export_v7(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    manifest = bundle.load_manifest()
    if not isinstance(manifest, dict):
        raise VariantError("export_v7 needs a manifest.json object at the bundle root")
    previous = manifest.get("export_version")
    manifest["export_version"] = "7" if isinstance(previous, str) else 7
    bundle.save_manifest(manifest)
    docs_touched = []
    pattern = re.compile(
        r"(export[_ ]version\W{0,5})" + re.escape(str(previous)) + r"\b", re.IGNORECASE
    )
    for path in sorted(bundle.out.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        new_text = (
            pattern.sub(lambda m: m.group(1) + "7", text)
            if previous is not None
            else text
        )
        if new_text != text:
            bundle.guard(path).write_text(new_text, encoding="utf-8")
            docs_touched.append(path.relative_to(bundle.out).as_posix())
    renamed = apply_renames(bundle, _pick_renames(bundle, 1, rng))
    return {
        "export_version_before": previous,
        "export_version_after": manifest["export_version"],
        "docs_touched": docs_touched,
        **renamed,
    }


def sentinel_elsewhere(
    bundle: Bundle, args: argparse.Namespace, rng: random.Random
) -> dict[str, Any]:
    candidates: list[tuple[Path, str]] = []
    for path in bundle.tables():
        if path.suffix.lower() not in {".parquet", ".pq"}:
            continue
        table = read_any(path)
        floats = [f.name for f in table.schema if pa.types.is_floating(f.type)]
        has_huge = any(
            (pc.max(pc.abs(pc.fill_null(table.column(n), 0.0))).as_py() or 0.0) >= HUGE
            for n in floats
        )
        if has_huge:
            continue  # the original sentinel table: move the trap elsewhere
        for name in floats:
            if (
                KEYLIKE_RE.search(name)
                or table.column(name).length() - table.column(name).null_count < 10
            ):
                continue
            if args.table and path.name != args.table:
                continue
            if args.column and name != args.column:
                continue
            candidates.append((path, name))
    if not candidates:
        raise VariantError("no float column in a sentinel-free table to inject into")
    path, name = rng.choice(candidates)
    table = read_any(path)
    values = table.column(name).to_pylist()
    live = [i for i, v in enumerate(values) if v is not None]
    count = max(1, round(len(live) * args.fraction))
    chosen = set(rng.sample(live, count))
    new_values = [FLOAT64_MAX if i in chosen else v for i, v in enumerate(values)]
    index = table.column_names.index(name)
    field = table.schema.field(index)
    mutated = table.set_column(index, field, pa.array(new_values, type=field.type))
    rel = path.relative_to(bundle.out).as_posix()

    def fn(t: pa.Table, p: Path) -> pa.Table | None:
        return mutated if p == path else None

    transform_tables(bundle, fn)
    return {"table": rel, "column": name, "injected": count, "value": FLOAT64_MAX}


HANDLERS: dict[
    str, Callable[[Bundle, argparse.Namespace, random.Random], dict[str, Any]]
] = {
    "categorical_treatment": categorical_treatment,
    "unbalanced": unbalanced,
    "drop_modality": drop_modality,
    "rename_columns": rename_columns,
    "export_v7": export_v7,
    "sentinel_elsewhere": sentinel_elsewhere,
}


def provenance_path(out: Path) -> Path:
    """Where the variant's provenance record goes (a sibling of OUT_DIR)."""

    return out.parent / f"{out.name}.variant.json"


def make_variant(src: Path, out: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Build one variant bundle and return its provenance record."""

    src, out = src.resolve(), out.resolve()
    if not src.is_dir():
        raise VariantError(f"source bundle is not a directory: {src}")
    if out == src or src in out.parents or out in src.parents:
        raise VariantError(
            "OUT_DIR must be outside the source bundle (and must not contain it)"
        )
    if out.exists() and any(out.iterdir()):
        if not args.force:
            raise VariantError(
                f"{out} exists and is not empty; pass --force to replace a previous variant"
            )
        if not provenance_path(out).is_file():
            raise VariantError(
                f"{out} was not made by this tool (no {provenance_path(out).name}); refusing to delete it"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    bundle = Bundle(src, out)
    copied = copy_bundle(bundle, link_assets=args.link_assets)
    rng = random.Random(args.seed)
    details = HANDLERS[args.variant](bundle, args, rng)
    record = {
        "variant": args.variant,
        "seed": args.seed,
        "source": str(src),
        "output": str(out),
        **copied,
        "mutation": details,
        "note": "CSV twins of mutated Parquet tables are regenerated from the Parquet and may differ in formatting from the export's own CSVs.",
    }
    provenance = provenance_path(out)
    if src == provenance.resolve() or src in provenance.resolve().parents:
        raise VariantError("provenance path would be inside the source bundle")
    provenance.write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return record


def build_parser() -> argparse.ArgumentParser:
    """Argument parser (exposed for tests)."""

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("src_bundle", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an OUT_DIR previously made by this tool",
    )
    parser.add_argument(
        "--link-assets",
        action="store_true",
        help="symlink skipped asset directories (best effort)",
    )
    parser.add_argument(
        "--columns", help="categorical_treatment: comma-separated treatment columns"
    )
    parser.add_argument("--control-label", default="C")
    parser.add_argument("--treated-label", default="Ni")
    parser.add_argument(
        "--unit-column", help="unbalanced: the unit id column (default: detected)"
    )
    parser.add_argument("--drop-fraction", type=float, default=0.1)
    parser.add_argument(
        "--modality", help="drop_modality: which modality (default: seeded choice)"
    )
    parser.add_argument(
        "--rename", action="append", help="rename_columns: OLD=NEW (repeatable)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="rename_columns: how many to rename when --rename is absent",
    )
    parser.add_argument(
        "--table", help="sentinel_elsewhere: restrict to this table file name"
    )
    parser.add_argument("--column", help="sentinel_elsewhere: restrict to this column")
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.05,
        help="sentinel_elsewhere: share of values to replace",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = build_parser().parse_args(argv)
    try:
        record = make_variant(args.src_bundle, args.out_dir, args)
    except VariantError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(record, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
