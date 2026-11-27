"""Build a teardown spec into one offline, interactive exploded-view page.

    build_teardown.py check SPEC.json
    build_teardown.py html SPEC.json -o PAGE.html [--three DIR] [--cache DIR]

``check`` validates the spec and prints what was built (parts, triangles, size in mm,
parts that still overlap when fully exploded, missing notes or source) as JSON.
``html`` writes a single page with three.js, the viewer and the meshes inlined, so it
opens from disk with no server and no network. three.js comes from an npm ``three``
package folder given with ``--three`` (for example a community teardown skill's
``node_modules/three``), or is downloaded once from the npm registry, checked against
its published sha512, and cached. Standard library only; no Node, npm or bundler.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import struct
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import teardown_geometry as geo

HERE = Path(__file__).resolve().parent
THREE_VERSION = "0.186.1"
THREE_TARBALL = f"https://registry.npmjs.org/three/-/three-{THREE_VERSION}.tgz"
THREE_INTEGRITY = "sha512-blFeqb49wRCSGUGj7gtpfnSGHy2lwDk94RhUmS1c/hTby70kvChbWpkJ4Pm1390LqzzvTmzgXKHPEafJwCb8jA=="
THREE_FILES = {
    "core": "build/three.core.js",
    "module": "build/three.module.js",
    "orbit": "examples/jsm/controls/OrbitControls.js",
    "room": "examples/jsm/environments/RoomEnvironment.js",
    "license": "LICENSE",
}


def _cache_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    if os.environ.get("TEARDOWN_CACHE"):
        return Path(os.environ["TEARDOWN_CACHE"])
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "clio-teardown"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "clio-teardown"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "clio-teardown"


def _from_folder(folder: Path) -> dict[str, str]:
    package = folder / "package" if (folder / "package" / "package.json").is_file() else folder
    if not (package / "package.json").is_file():
        raise geo.SpecError(f"{folder} is not an npm 'three' package folder (no package.json)")
    meta = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if meta.get("name") != "three":
        raise geo.SpecError(f"{folder} holds '{meta.get('name')}', not three")
    out: dict[str, str] = {"version": str(meta.get("version", ""))}
    for key, rel in THREE_FILES.items():
        path = package / rel
        if not path.is_file():
            if key == "core":
                out[key] = ""
                continue
            raise geo.SpecError(f"{path} is missing: use three 0.160 or newer")
        out[key] = path.read_text(encoding="utf-8")
    return out


def _download(cache: Path) -> Path:
    target = cache / f"three-{THREE_VERSION}"
    if (target / "package" / "package.json").is_file():
        return target
    print(f"Downloading three {THREE_VERSION} from the npm registry (once)...", file=sys.stderr)
    with urllib.request.urlopen(THREE_TARBALL, timeout=120) as response:
        blob = response.read()
    digest = "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode()
    if digest != THREE_INTEGRITY:
        raise geo.SpecError("the downloaded three.js does not match its published sha512; not using it")
    wanted = {f"package/{rel}" for rel in THREE_FILES.values()} | {"package/package.json"}
    staging = Path(tempfile.mkdtemp(prefix="three-", dir=cache))
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name in wanted and member.isfile():
                source = tar.extractfile(member)
                if source is None:
                    continue
                dest = staging / member.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source.read())
    try:
        staging.rename(target)
    except OSError:
        return staging
    return target


def three_sources(three_dir: str | None, cache_dir: str | None) -> dict[str, str]:
    """three.js sources from a given package folder, or the checked, cached download."""
    if three_dir:
        return _from_folder(Path(three_dir))
    cache = _cache_dir(cache_dir)
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache = Path(tempfile.gettempdir()) / "clio-teardown"
        cache.mkdir(parents=True, exist_ok=True)
    return _from_folder(_download(cache))


def _pack(data: bytes) -> str:
    return base64.b64encode(gzip.compress(data, compresslevel=9, mtime=0)).decode("ascii")


def model_payload(assembly: geo.Assembly) -> tuple[dict[str, Any], bytes]:
    """The page's metadata and one binary buffer of every part's mesh."""
    buf = bytearray()
    parts: list[dict[str, Any]] = []
    for p in assembly.parts:
        m = p.mesh
        pos_at = len(buf)
        buf += struct.pack(f"<{len(m.positions)}f", *m.positions)
        nrm_at = len(buf)
        buf += struct.pack(f"<{len(m.normals)}b", *(max(-127, min(127, round(v * 127))) for v in m.normals))
        while len(buf) % 4:
            buf.append(0)
        idx_at = len(buf)
        buf += struct.pack(f"<{len(m.indices)}I", *m.indices)
        row: dict[str, Any] = {
            "id": p.id,
            "name": p.name,
            "subsystem": p.subsystem,
            "material": p.material,
            "color": p.color,
            "note": p.note,
            "accent": p.accent,
            "cutaway": p.cutaway,
            "pivot": p.pivot,
            "explode": {"direction": p.explode_direction, "distance": p.explode_distance, "order": p.explode_order},
            "mesh": {"vertices": m.vertex_count, "triangles": m.triangle_count, "positions": pos_at, "normals": nrm_at, "indices": idx_at},
        }
        if p.motion is not None:
            row["motion"] = {
                "axis": p.motion.axis,
                "angle": [round(a, 4) for a in p.motion.angle],
                "translate": [[round(v, 4) for v in t] for t in p.motion.translate],
            }
        parts.append(row)
    meta = {
        "title": assembly.title,
        "subtitle": assembly.subtitle,
        "summary": assembly.summary,
        "source": assembly.source,
        "accent": assembly.accent,
        "background": assembly.background,
        "subsystems": assembly.subsystems,
        "input": assembly.input,
        "steps": assembly.steps,
        "stages": assembly.stages,
        "camera": assembly.camera,
        "parts": parts,
    }
    return meta, bytes(buf)


def _script_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


BOOT = r"""
(async () => {
  const fail = (msg) => { document.body.dataset.ready = "error"; const el = document.getElementById("td-loading"); if (el) el.textContent = msg; };
  try {
    if (!("DecompressionStream" in window)) { fail("This browser is too old to open the page: use a current Chrome, Edge, Firefox or Safari."); return; }
    const raw = (id) => Uint8Array.from(atob(document.getElementById(id).textContent.trim()), (c) => c.charCodeAt(0));
    const inflate = (id) => new Response(new Blob([raw(id)]).stream().pipeThrough(new DecompressionStream("gzip")));
    const text = async (id) => (await inflate(id)).text();
    const url = (src) => URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    const core = await text("td-three-core");
    let three = await text("td-three");
    if (core) three = three.split("'./three.core.js'").join(JSON.stringify(url(core)));
    const threeUrl = url(three);
    const bare = (src) => src.split("from 'three'").join("from " + JSON.stringify(threeUrl));
    const orbitUrl = url(bare(await text("td-orbit")));
    const roomUrl = url(bare(await text("td-room")));
    let viewer = await text("td-viewer");
    viewer = viewer.split("'three/addons/controls/OrbitControls.js'").join(JSON.stringify(orbitUrl));
    viewer = viewer.split("'three/addons/environments/RoomEnvironment.js'").join(JSON.stringify(roomUrl));
    viewer = viewer.split("from 'three'").join("from " + JSON.stringify(threeUrl));
    window.__TEARDOWN__ = { meta: JSON.parse(document.getElementById("td-meta").textContent), buffer: await (await inflate("td-mesh")).arrayBuffer() };
    await import(url(viewer));
  } catch (err) { console.error(err); fail("The page could not start: " + (err && err.message ? err.message : err)); }
})();
"""


def build_html(assembly: geo.Assembly, three: dict[str, str]) -> str:
    meta, mesh = model_payload(assembly)
    meta["generator"] = {"three": three.get("version", ""), "tool": "CLIO teardown plugin"}
    css = (HERE / "viewer.css").read_text(encoding="utf-8")
    viewer = (HERE / "viewer.js").read_text(encoding="utf-8")
    title = assembly.title.replace("&", "&amp;").replace("<", "&lt;")
    blobs = {
        "td-three-core": three.get("core", "").encode(),
        "td-three": three["module"].encode(),
        "td-orbit": three["orbit"].encode(),
        "td-room": three["room"].encode(),
        "td-viewer": viewer.encode(),
        "td-mesh": mesh,
    }
    packed = "\n".join(f'<script type="application/octet-stream" id="{k}">{_pack(v)}</script>' for k, v in blobs.items())
    license_text = three["license"].replace("</", "<\\/")
    return f"""<!doctype html>
<!-- Built by the CLIO teardown plugin. Includes three.js {three.get("version", "")} (MIT License, Copyright three.js authors; full text in #td-licenses).
     Viewer approach adapted from elvarofficial/teardown (MIT). Opens offline: everything it needs is in this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - exploded view</title>
<style>{css}</style>
</head>
<body>
<div id="td-loading" class="td-loading">Loading the model...</div>
<script type="application/json" id="td-meta">{_script_json(meta)}</script>
<script type="text/plain" id="td-licenses">three.js
{license_text}</script>
{packed}
<script>{BOOT}</script>
</body>
</html>
"""


def check_report(assembly: geo.Assembly) -> dict[str, Any]:
    lo, hi = assembly.bounds(0.0)
    elo, ehi = assembly.bounds(1.0)
    return {
        "title": assembly.title,
        "parts": len(assembly.parts),
        "subsystems": [s["id"] for s in assembly.subsystems],
        "triangles": assembly.triangle_count(),
        "assembled_size_mm": [round(hi[k] - lo[k], 2) for k in range(3)],
        "exploded_size_mm": [round(ehi[k] - elo[k], 2) for k in range(3)],
        "explode_stages": assembly.stages,
        "moving_parts": [p.id for p in assembly.parts if p.motion is not None],
        "steps": len(assembly.steps),
        "still_overlapping_when_exploded": [{"a": a, "b": b, "share": round(s, 2)} for a, b, s in geo.overlaps(assembly, 1.0)],
        "inside_out_parts": [p.id for p in assembly.parts if p.mesh.signed_volume() < 0],
        "notes": assembly.notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate the spec and report what it builds")
    check.add_argument("spec")
    html = sub.add_parser("html", help="write the offline page")
    html.add_argument("spec")
    html.add_argument("-o", "--output", required=True)
    html.add_argument("--three", help="an npm 'three' package folder to use instead of the download")
    html.add_argument("--cache", help="where the downloaded three.js is kept")
    args = parser.parse_args(argv)
    spec_path = Path(args.spec).resolve()
    try:
        assembly = geo.build_assembly(geo.load_spec(spec_path), spec_path.parent)
        if args.command == "check":
            print(json.dumps(check_report(assembly), indent=1))
            return 0
        page = build_html(assembly, three_sources(args.three, args.cache))
    except geo.SpecError as exc:
        print(f"spec error: {exc}", file=sys.stderr)
        return 2
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    report = check_report(assembly)
    report["page"] = str(out)
    report["page_kb"] = round(out.stat().st_size / 1024)
    report["file_url"] = out.as_uri()
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
