"""Parts, meshes, explode offsets and motion for a teardown assembly spec.

One JSON spec (see ``references/spec.md``) describes any assembly: parts built from
primitive shapes in real units, the subsystem each belongs to, how it moves out in the
exploded view, and how one input drives it. This module turns the spec into baked meshes
that both renderers use unchanged: the browser page (``build_teardown.py``) and Blender
(``teardown-in-blender/scripts/build_blend.py``). Standard library only, so it also runs
inside Blender's own Python.

Coordinates are Z up, in millimetres after unit conversion. Each part's vertices are
stored relative to its pivot, so a renderer places the part at ``pivot + explode offset
+ motion translation`` and turns it by the motion angle about the motion axis.
"""

from __future__ import annotations

import itertools
import json
import math
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Vec = tuple[float, float, float]
Vec2 = tuple[float, float]
Mat = tuple[float, float, float, float, float, float, float, float, float]

UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}
SHAPES = (
    "box",
    "cylinder",
    "tube",
    "cone",
    "sphere",
    "torus",
    "lathe",
    "extrude",
    "gear",
    "hex",
    "rod",
    "sweep",
    "spring",
    "stl",
)
MATERIALS = (
    "steel",
    "aluminium",
    "cast-iron",
    "brass",
    "copper",
    "gold",
    "chrome",
    "plastic",
    "rubber",
    "glass",
    "pcb",
    "ceramic",
    "wood",
    "painted",
)
MOTIONS = ("rotate", "slide", "rigid")
SMOOTH_ANGLE = 35.0
SAMPLES = 241
MAX_COPIES = 500


class SpecError(ValueError):
    """The spec cannot be built; the message names the field to fix."""


# --- vectors and rotations -------------------------------------------------------------


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(a: Vec) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Vec, fallback: Vec = (0.0, 0.0, 1.0)) -> Vec:
    n = _length(a)
    return _mul(a, 1.0 / n) if n > 1e-12 else fallback


IDENTITY: Mat = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def _matmul(a: Mat, b: Mat) -> Mat:
    return (
        a[0] * b[0] + a[1] * b[3] + a[2] * b[6],
        a[0] * b[1] + a[1] * b[4] + a[2] * b[7],
        a[0] * b[2] + a[1] * b[5] + a[2] * b[8],
        a[3] * b[0] + a[4] * b[3] + a[5] * b[6],
        a[3] * b[1] + a[4] * b[4] + a[5] * b[7],
        a[3] * b[2] + a[4] * b[5] + a[5] * b[8],
        a[6] * b[0] + a[7] * b[3] + a[8] * b[6],
        a[6] * b[1] + a[7] * b[4] + a[8] * b[7],
        a[6] * b[2] + a[7] * b[5] + a[8] * b[8],
    )


def _apply(m: Mat, v: Vec) -> Vec:
    return (
        m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
        m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
        m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
    )


def axis_angle(axis: Vec, degrees: float) -> Mat:
    """The rotation by ``degrees`` about ``axis`` (right-handed)."""
    x, y, z = _unit(axis)
    a = math.radians(degrees)
    c, s, t = math.cos(a), math.sin(a), 1.0 - math.cos(a)
    return (
        t * x * x + c,
        t * x * y - s * z,
        t * x * z + s * y,
        t * x * y + s * z,
        t * y * y + c,
        t * y * z - s * x,
        t * x * z - s * y,
        t * y * z + s * x,
        t * z * z + c,
    )


def euler_xyz(degrees: Sequence[float]) -> Mat:
    """Turn about world X, then Y, then Z (Blender's XYZ Euler)."""
    rx = axis_angle((1.0, 0.0, 0.0), degrees[0])
    ry = axis_angle((0.0, 1.0, 0.0), degrees[1])
    rz = axis_angle((0.0, 0.0, 1.0), degrees[2])
    return _matmul(rz, _matmul(ry, rx))


def _align_z(direction: Vec) -> Mat:
    """A rotation taking +Z onto ``direction``."""
    d = _unit(direction)
    z: Vec = (0.0, 0.0, 1.0)
    c = _dot(z, d)
    if c > 1.0 - 1e-9:
        return IDENTITY
    if c < -1.0 + 1e-9:
        return axis_angle((1.0, 0.0, 0.0), 180.0)
    return axis_angle(_cross(z, d), math.degrees(math.acos(max(-1.0, min(1.0, c)))))


# --- meshes ----------------------------------------------------------------------------


@dataclass
class Mesh:
    """Triangles with per-vertex normals; hard edges are split vertices."""

    positions: list[float] = field(default_factory=list)
    normals: list[float] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return len(self.positions) // 3

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3

    def vertex(self, p: Vec, n: Vec) -> int:
        self.positions.extend(p)
        self.normals.extend(_unit(n))
        return self.vertex_count - 1

    def triangle(self, a: int, b: int, c: int) -> None:
        self.indices.extend((a, b, c))

    def extend(self, other: Mesh) -> None:
        base = self.vertex_count
        self.positions.extend(other.positions)
        self.normals.extend(other.normals)
        self.indices.extend(i + base for i in other.indices)

    def transformed(self, rotation: Mat, offset: Vec) -> Mesh:
        out = Mesh(indices=list(self.indices))
        for i in range(0, len(self.positions), 3):
            p = _apply(rotation, (self.positions[i], self.positions[i + 1], self.positions[i + 2]))
            out.positions.extend(_add(p, offset))
            out.normals.extend(_apply(rotation, (self.normals[i], self.normals[i + 1], self.normals[i + 2])))
        return out

    def points(self) -> Iterable[Vec]:
        p = self.positions
        for i in range(0, len(p), 3):
            yield (p[i], p[i + 1], p[i + 2])

    def bounds(self) -> tuple[Vec, Vec]:
        if not self.positions:
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        xs, ys, zs = self.positions[0::3], self.positions[1::3], self.positions[2::3]
        return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

    def signed_volume(self) -> float:
        """Positive for a closed mesh whose triangles face outwards."""
        p = self.positions
        total = 0.0
        for k in range(0, len(self.indices), 3):
            a, b, c = (self.indices[k + j] * 3 for j in range(3))
            va: Vec = (p[a], p[a + 1], p[a + 2])
            vb: Vec = (p[b], p[b + 1], p[b + 2])
            vc: Vec = (p[c], p[c + 1], p[c + 2])
            total += _dot(va, _cross(vb, vc))
        return total / 6.0


def _segments_for(radius: float, requested: Any = None) -> int:
    if requested is not None:
        return max(3, min(256, int(requested)))
    chord = max(0.8, radius * 0.1)
    return max(16, min(96, round(2 * math.pi * max(radius, 1e-6) / chord)))


def _smooth_normals(normals: Sequence[Vec2], closed: bool) -> list[tuple[Vec2, Vec2]]:
    """Each segment's normal at its start and end, averaged across shallow corners."""
    n = len(normals)
    limit = math.cos(math.radians(SMOOTH_ANGLE))

    def blend(a: Vec2, b: Vec2) -> Vec2:
        if a[0] * b[0] + a[1] * b[1] < limit:
            return a
        x, y = a[0] + b[0], a[1] + b[1]
        length = math.hypot(x, y) or 1.0
        return (x / length, y / length)

    out: list[tuple[Vec2, Vec2]] = []
    for i, normal in enumerate(normals):
        has_prev = closed or i > 0
        has_next = closed or i < n - 1
        start = blend(normal, normals[i - 1]) if has_prev else normal
        end = blend(normal, normals[(i + 1) % n]) if has_next else normal
        out.append((start, end))
    return out


def revolve(profile: Sequence[Vec2], segments: int, closed: bool = False) -> Mesh:
    """Turn a counter-clockwise (radius, z) profile about Z into a solid."""
    pts = [(max(0.0, float(r)), float(z)) for r, z in profile]
    count = len(pts) if closed else len(pts) - 1
    segs: list[tuple[Vec2, Vec2]] = []
    for i in range(count):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        if a == b or (a[0] == 0.0 and b[0] == 0.0):
            continue
        segs.append((a, b))
    seg_normals: list[Vec2] = []
    for a, b in segs:
        dr, dz = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dr, dz)
        seg_normals.append((dz / length, -dr / length))
    ends = _smooth_normals(seg_normals, closed)
    mesh = Mesh()
    angles = [2 * math.pi * j / segments for j in range(segments + 1)]
    for (a, b), (na, nb) in zip(segs, ends, strict=True):
        ring_a: list[int] = []
        ring_b: list[int] = []
        for t in angles:
            c, s = math.cos(t), math.sin(t)
            ring_a.append(mesh.vertex((a[0] * c, a[0] * s, a[1]), (na[0] * c, na[0] * s, na[1])))
            ring_b.append(mesh.vertex((b[0] * c, b[0] * s, b[1]), (nb[0] * c, nb[0] * s, nb[1])))
        for j in range(segments):
            if a[0] > 0.0:
                mesh.triangle(ring_a[j], ring_a[j + 1], ring_b[j])
            if b[0] > 0.0:
                mesh.triangle(ring_a[j + 1], ring_b[j + 1], ring_b[j])
    return mesh


def _signed_area(poly: Sequence[Vec2]) -> float:
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def _clean(poly: Sequence[Sequence[float]], ccw: bool) -> list[Vec2]:
    out: list[Vec2] = []
    for p in poly:
        q = (float(p[0]), float(p[1]))
        if not out or math.dist(out[-1], q) > 1e-9:
            out.append(q)
    if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-9:
        out.pop()
    if len(out) < 3:
        raise SpecError("an outline needs at least 3 distinct points")
    if (_signed_area(out) > 0) != ccw:
        out.reverse()
    return out


def _cross2(o: Vec2, a: Vec2, b: Vec2) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(p1: Vec2, p2: Vec2, q1: Vec2, q2: Vec2) -> bool:
    """Proper intersection of two segments (shared endpoints do not count)."""
    if p1 in (q1, q2) or p2 in (q1, q2):
        return False
    d1, d2 = _cross2(q1, q2, p1), _cross2(q1, q2, p2)
    d3, d4 = _cross2(p1, p2, q1), _cross2(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 < 0 and d3 * d4 < 0


def _bridge(outer: list[Vec2], holes: list[list[Vec2]]) -> list[Vec2]:
    """Join holes into the outline with zero-width cuts, rightmost hole first."""
    poly = list(outer)
    remaining = sorted(holes, key=lambda h: -max(p[0] for p in h))
    while remaining:
        hole = remaining.pop(0)
        m_index = max(range(len(hole)), key=lambda i: hole[i][0])
        m = hole[m_index]
        others = [h for h in remaining]
        candidates = sorted(range(len(poly)), key=lambda i: math.dist(poly[i], m))
        chosen = None
        for i in candidates:
            v = poly[i]
            blocked = False
            for j in range(len(poly)):
                if _segments_cross(m, v, poly[j], poly[(j + 1) % len(poly)]):
                    blocked = True
                    break
            if not blocked:
                for h in [hole, *others]:
                    for j in range(len(h)):
                        if _segments_cross(m, v, h[j], h[(j + 1) % len(h)]):
                            blocked = True
                            break
                    if blocked:
                        break
            if not blocked:
                chosen = i
                break
        if chosen is None:
            raise SpecError("a hole could not be joined to its outline: is it inside it?")
        ring = hole[m_index:] + hole[:m_index]
        poly = poly[: chosen + 1] + ring + [m] + poly[chosen:]
    return poly


def _in_triangle(p: Vec2, a: Vec2, b: Vec2, c: Vec2) -> bool:
    return _cross2(a, b, p) >= 0 and _cross2(b, c, p) >= 0 and _cross2(c, a, p) >= 0


def triangulate(poly: Sequence[Vec2]) -> list[tuple[int, int, int]]:
    """Ear-clip a counter-clockwise simple polygon (bridged holes allowed)."""
    idx = list(range(len(poly)))
    tris: list[tuple[int, int, int]] = []
    i = 0
    stall = 0
    while len(idx) > 3:
        n = len(idx)
        a, b, c = idx[(i - 1) % n], idx[i % n], idx[(i + 1) % n]
        pa, pb, pc = poly[a], poly[b], poly[c]
        ear = _cross2(pa, pb, pc) > 1e-12
        if ear:
            for k in idx:
                if k in (a, b, c):
                    continue
                pk = poly[k]
                if pk in (pa, pb, pc):
                    continue
                if _in_triangle(pk, pa, pb, pc):
                    ear = False
                    break
        if ear:
            tris.append((a, b, c))
            idx.pop(i % n)
            stall = 0
            i = max(0, (i % n) - 1)
            continue
        i += 1
        stall += 1
        if stall > n:
            # Only degenerate or collinear corners remain: drop the flattest one.
            flat = min(
                range(n),
                key=lambda k: abs(_cross2(poly[idx[k - 1]], poly[idx[k]], poly[idx[(k + 1) % n]])),
            )
            idx.pop(flat)
            stall = 0
    if len(idx) == 3 and _cross2(poly[idx[0]], poly[idx[1]], poly[idx[2]]) > 0:
        tris.append((idx[0], idx[1], idx[2]))
    return tris


def extrude(
    outline: Sequence[Sequence[float]],
    holes: Sequence[Sequence[Sequence[float]]],
    thickness: float,
) -> Mesh:
    """An outline (with holes) in XY, extruded from z=0 up to ``thickness``."""
    outer = _clean(outline, ccw=True)
    inner = [_clean(h, ccw=False) for h in holes]
    mesh = Mesh()
    for ring in [outer, *inner]:
        n = len(ring)
        normals: list[Vec2] = []
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            normals.append((dy / length, -dx / length))
        ends = _smooth_normals(normals, closed=True)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            na, nb = ends[i]
            v0 = mesh.vertex((a[0], a[1], 0.0), (na[0], na[1], 0.0))
            v1 = mesh.vertex((b[0], b[1], 0.0), (nb[0], nb[1], 0.0))
            v2 = mesh.vertex((b[0], b[1], thickness), (nb[0], nb[1], 0.0))
            v3 = mesh.vertex((a[0], a[1], thickness), (na[0], na[1], 0.0))
            mesh.triangle(v0, v1, v2)
            mesh.triangle(v0, v2, v3)
    poly = _bridge(outer, inner)
    tris = triangulate(poly)
    top = [mesh.vertex((p[0], p[1], thickness), (0.0, 0.0, 1.0)) for p in poly]
    bottom = [mesh.vertex((p[0], p[1], 0.0), (0.0, 0.0, -1.0)) for p in poly]
    for a, b, c in tris:
        mesh.triangle(top[a], top[b], top[c])
        mesh.triangle(bottom[a], bottom[c], bottom[b])
    return mesh


def circle(cx: float, cy: float, r: float, segments: int | None = None) -> list[Vec2]:
    n = segments or _segments_for(r)
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def gear_outline(teeth: int, module: float, pressure_angle: float = 20.0) -> list[Vec2]:
    """An involute spur gear's outline, centred on the origin."""
    if teeth < 4:
        raise SpecError("a gear needs at least 4 teeth")
    rp = module * teeth / 2.0
    rb = rp * math.cos(math.radians(pressure_angle))
    ra = rp + module
    rf = max(0.2 * rp, rp - 1.25 * module)

    def inv(r: float) -> float:
        if r <= rb:
            return 0.0
        a = math.acos(rb / r)
        return math.tan(a) - a

    half_tooth = math.pi / (2 * teeth) + inv(rp)
    radii = [max(rf, rb) + (ra - max(rf, rb)) * k / 7 for k in range(8)]
    out: list[Vec2] = []
    pitch = 2 * math.pi / teeth
    for t in range(teeth):
        centre = t * pitch
        flank = [(r, max(0.04 * pitch, half_tooth - inv(r))) for r in radii]
        left = [(rf, centre - half_tooth)] if rf < rb else []
        right = [(rf, centre + half_tooth)] if rf < rb else []
        tooth = left + [(r, centre - a) for r, a in flank] + [(r, centre + a) for r, a in reversed(flank)] + right
        out.extend((r * math.cos(a), r * math.sin(a)) for r, a in tooth)
    return out


def sweep(path: Sequence[Vec], radius: float, closed: bool = False, segments: int | None = None) -> Mesh:
    """A round wire of ``radius`` along a polyline, with flat end caps when open."""
    pts = [p for i, p in enumerate(path) if i == 0 or _length(_sub(p, path[i - 1])) > 1e-9]
    if len(pts) < 2:
        raise SpecError("a sweep path needs at least 2 distinct points")
    n = _segments_for(radius, segments)
    count = len(pts)
    tangents: list[Vec] = []
    for i in range(count):
        if closed:
            t = _sub(pts[(i + 1) % count], pts[i - 1])
        else:
            t = _sub(pts[min(i + 1, count - 1)], pts[max(i - 1, 0)])
        tangents.append(_unit(t))
    seed: Vec = (0.0, 0.0, 1.0) if abs(tangents[0][2]) < 0.9 else (1.0, 0.0, 0.0)
    normal = _unit(_cross(_cross(tangents[0], seed), tangents[0]))
    frames: list[tuple[Vec, Vec]] = []
    for i, t in enumerate(tangents):
        if i:
            normal = _unit(_sub(normal, _mul(t, _dot(normal, t))), normal)
        frames.append((normal, _cross(t, normal)))
    mesh = Mesh()
    rings: list[list[int]] = []
    rims: list[list[Vec]] = []
    for p, (u, v) in zip(pts, frames, strict=True):
        ring: list[int] = []
        rim: list[Vec] = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            d = _add(_mul(u, math.cos(a)), _mul(v, math.sin(a)))
            rim.append(_add(p, _mul(d, radius)))
            ring.append(mesh.vertex(rim[-1], d))
        rings.append(ring)
        rims.append(rim)
    pairs = count if closed else count - 1
    for i in range(pairs):
        a, b = rings[i], rings[(i + 1) % count]
        for k in range(n):
            mesh.triangle(a[k], a[k + 1], b[k])
            mesh.triangle(a[k + 1], b[k + 1], b[k])
    if not closed:
        for ring_index, sign in ((0, -1.0), (count - 1, 1.0)):
            centre = pts[ring_index]
            t = _mul(tangents[ring_index], sign)
            c = mesh.vertex(centre, t)
            cap = [mesh.vertex(q, t) for q in rims[ring_index][:n]]
            for k in range(n):
                v0, v1 = cap[k], cap[(k + 1) % n]
                if sign > 0:
                    mesh.triangle(c, v0, v1)
                else:
                    mesh.triangle(c, v1, v0)
    return mesh


def read_stl(path: Path, scale: float) -> Mesh:
    """An ASCII or binary STL, flat shaded."""
    data = path.read_bytes()
    tris: list[tuple[Vec, Vec, Vec]] = []
    if len(data) >= 84 and 84 + 50 * struct.unpack_from("<I", data, 80)[0] == len(data):
        for k in range(struct.unpack_from("<I", data, 80)[0]):
            f = struct.unpack_from("<12f", data, 84 + 50 * k)
            tris.append(((f[3], f[4], f[5]), (f[6], f[7], f[8]), (f[9], f[10], f[11])))
    else:
        verts: list[Vec] = []
        for line in data.decode("utf-8", "replace").splitlines():
            parts = line.split()
            if parts[:1] == ["vertex"] and len(parts) >= 4:
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        tris = [(verts[i], verts[i + 1], verts[i + 2]) for i in range(0, len(verts) - 2, 3)]
    if not tris:
        raise SpecError(f"no triangles read from {path.name}")
    mesh = Mesh()
    for a, b, c in tris:
        a, b, c = _mul(a, scale), _mul(b, scale), _mul(c, scale)
        n = _unit(_cross(_sub(b, a), _sub(c, a)))
        mesh.triangle(mesh.vertex(a, n), mesh.vertex(b, n), mesh.vertex(c, n))
    return mesh


# --- spec reading ----------------------------------------------------------------------


def _num(obj: dict[str, Any], key: str, where: str, default: float | None = None, positive: bool = False) -> float:
    value = obj.get(key, default)
    if value is None:
        raise SpecError(f"{where}: '{key}' is required")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise SpecError(f"{where}: '{key}' must be a number")
    if positive and value <= 0:
        raise SpecError(f"{where}: '{key}' must be greater than 0")
    return float(value)


def _vec(value: Any, where: str, default: Vec | None = None) -> Vec:
    if value is None:
        if default is None:
            raise SpecError(f"{where} is required")
        return default
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(isinstance(v, (int, float)) for v in value):
        raise SpecError(f"{where} must be [x, y, z]")
    return (float(value[0]), float(value[1]), float(value[2]))


def _points2(value: Any, where: str, scale: float) -> list[Vec2]:
    if not isinstance(value, list) or len(value) < 2:
        raise SpecError(f"{where} must be a list of [x, y] points")
    out: list[Vec2] = []
    for p in value:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise SpecError(f"{where} must be a list of [x, y] points")
        out.append((float(p[0]) * scale, float(p[1]) * scale))
    return out


def _hole_list(value: Any, where: str, scale: float) -> list[list[Vec2]]:
    holes: list[list[Vec2]] = []
    for k, hole in enumerate(value or []):
        if isinstance(hole, dict) and "circle" in hole:
            cx, cy, r = (float(v) * scale for v in hole["circle"])
            holes.append(circle(cx, cy, r, hole.get("segments")))
        else:
            holes.append(_points2(hole, f"{where}[{k}]", scale))
    return holes


def build_shape(shape: dict[str, Any], where: str, scale: float, base_dir: Path) -> Mesh:
    """One shape's mesh in its own frame (before its position and rotation)."""
    kind = shape.get("type")
    if kind not in SHAPES:
        raise SpecError(f"{where}: 'type' must be one of {', '.join(SHAPES)}")
    seg = shape.get("segments")

    def n(key: str, default: float | None = None, positive: bool = True) -> float:
        return _num(shape, key, where, default, positive) * scale

    mesh: Mesh
    if kind == "box":
        sx, sy, sz = (abs(v) * scale for v in _vec(shape.get("size"), f"{where}.size"))
        mesh = extrude([(-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)], [], sz)
        mesh = mesh.transformed(IDENTITY, (0.0, 0.0, -sz / 2))
    elif kind == "cylinder":
        r, h = n("radius"), n("height")
        mesh = revolve([(0, 0), (r, 0), (r, h), (0, h)], _segments_for(r, seg))
    elif kind == "tube":
        ro, ri, h = n("outer_radius"), n("inner_radius"), n("height")
        if ri >= ro:
            raise SpecError(f"{where}: inner_radius must be smaller than outer_radius")
        mesh = revolve([(ri, 0), (ro, 0), (ro, h), (ri, h)], _segments_for(ro, seg), closed=True)
    elif kind == "cone":
        r0, r1, h = n("radius_bottom", positive=False), n("radius_top", 0.0, positive=False), n("height")
        mesh = revolve([(0, 0), (r0, 0), (r1, h), (0, h)], _segments_for(max(r0, r1), seg))
    elif kind == "sphere":
        r = n("radius")
        k = max(8, _segments_for(r, seg) // 2)
        prof = [(r * math.sin(math.pi * i / k), -r * math.cos(math.pi * i / k)) for i in range(k + 1)]
        mesh = revolve(prof, _segments_for(r, seg))
    elif kind == "torus":
        big, small = n("radius"), n("tube")
        k = _segments_for(small, shape.get("tube_segments"))
        prof = [(big + small * math.cos(2 * math.pi * i / k), small * math.sin(2 * math.pi * i / k)) for i in range(k)]
        mesh = revolve(prof, _segments_for(big + small, seg), closed=True)
    elif kind == "lathe":
        prof = _points2(shape.get("profile"), f"{where}.profile", scale)
        if _signed_area(prof) < 0:
            prof.reverse()
        mesh = revolve(prof, _segments_for(max(p[0] for p in prof), seg), closed=bool(shape.get("closed", True)))
    elif kind == "extrude":
        outline = _points2(shape.get("outline"), f"{where}.outline", scale)
        mesh = extrude(outline, _hole_list(shape.get("holes"), f"{where}.holes", scale), n("thickness"))
    elif kind == "gear":
        teeth = int(_num(shape, "teeth", where, positive=True))
        module = n("module")
        outline = gear_outline(teeth, module, _num(shape, "pressure_angle", where, 20.0, positive=True))
        holes = _hole_list(shape.get("holes"), f"{where}.holes", scale)
        if shape.get("bore"):
            holes.insert(0, circle(0.0, 0.0, n("bore") / 2))
        mesh = extrude(outline, holes, n("thickness"))
    elif kind == "hex":
        af, h = n("across_flats"), n("height")
        rc = af / math.sqrt(3.0)
        outline = [(rc * math.cos(math.pi / 3 * k + math.pi / 6), rc * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)]
        holes = [circle(0.0, 0.0, n("bore") / 2)] if shape.get("bore") else []
        mesh = extrude(outline, holes, h)
    elif kind == "rod":
        a = _mul(_vec(shape.get("from"), f"{where}.from"), scale)
        b = _mul(_vec(shape.get("to"), f"{where}.to"), scale)
        r = n("radius")
        length = _length(_sub(b, a))
        if length <= 0:
            raise SpecError(f"{where}: 'from' and 'to' must differ")
        mesh = revolve([(0, 0), (r, 0), (r, length), (0, length)], _segments_for(r, seg))
        mesh = mesh.transformed(_align_z(_sub(b, a)), a)
    elif kind in ("sweep", "spring"):
        r = n("radius" if kind == "sweep" else "wire")
        if kind == "sweep":
            raw = shape.get("path")
            if not isinstance(raw, list) or len(raw) < 2:
                raise SpecError(f"{where}.path must be a list of [x, y, z] points")
            path = [_mul(_vec(p, f"{where}.path"), scale) for p in raw]
            closed = bool(shape.get("closed", False))
        else:
            coil, pitch, turns = n("radius"), n("pitch"), _num(shape, "turns", where, positive=True)
            steps = max(12, int(turns * 24))
            path = [
                (
                    coil * math.cos(2 * math.pi * turns * i / steps),
                    coil * math.sin(2 * math.pi * turns * i / steps),
                    pitch * turns * i / steps,
                )
                for i in range(steps + 1)
            ]
            closed = False
        mesh = sweep(path, r, closed, seg)
    else:
        file = shape.get("path")
        if not isinstance(file, str):
            raise SpecError(f"{where}: 'path' must name an STL file")
        target = (base_dir / file).resolve()
        if not target.is_file():
            raise SpecError(f"{where}: {target} does not exist")
        mesh = read_stl(target, scale)
    offset = _mul(_vec(shape.get("position"), f"{where}.position", (0.0, 0.0, 0.0)), scale)
    rotation = euler_xyz(_vec(shape.get("rotation"), f"{where}.rotation", (0.0, 0.0, 0.0)))
    return mesh.transformed(rotation, offset)


@dataclass
class Motion:
    """Sampled motion over the input range: translation (mm) and angle (deg) per sample."""

    axis: Vec
    translate: list[Vec]
    angle: list[float]


@dataclass
class Part:
    id: str
    name: str
    subsystem: str
    material: str
    color: str | None
    note: str
    accent: bool
    cutaway: bool
    pivot: Vec
    mesh: Mesh
    explode_direction: Vec
    explode_distance: float
    explode_order: int
    motion: Motion | None
    centroid: Vec = (0.0, 0.0, 0.0)


@dataclass
class Assembly:
    title: str
    subtitle: str
    summary: str
    source: dict[str, Any]
    accent: str
    background: str
    subsystems: list[dict[str, Any]]
    input: dict[str, Any] | None
    steps: list[dict[str, Any]]
    parts: list[Part]
    stages: int
    notes: list[str]
    camera: dict[str, Any]

    def explode_offset(self, part: Part, amount: float) -> Vec:
        """Where ``part`` sits at explode ``amount`` (0 assembled, 1 fully out)."""
        local = min(1.0, max(0.0, amount * self.stages - part.explode_order))
        smooth = local * local * (3 - 2 * local)
        return _mul(part.explode_direction, part.explode_distance * smooth)

    def input_samples(self) -> list[float]:
        if not self.input:
            return [0.0]
        lo, hi = float(self.input["min"]), float(self.input["max"])
        return [lo + (hi - lo) * k / (SAMPLES - 1) for k in range(SAMPLES)]

    def bounds(self, explode: float = 0.0) -> tuple[Vec, Vec]:
        lo: list[float] = [math.inf] * 3
        hi: list[float] = [-math.inf] * 3
        for part in self.parts:
            (a, b) = part.mesh.bounds()
            shift = _add(part.pivot, self.explode_offset(part, explode))
            for k in range(3):
                lo[k] = min(lo[k], a[k] + shift[k])
                hi[k] = max(hi[k], b[k] + shift[k])
        if not self.parts:
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        return ((lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2]))

    def triangle_count(self) -> int:
        return sum(p.mesh.triangle_count for p in self.parts)


def _interp(table: list[list[float]], u: float, columns: int) -> list[float]:
    if u <= table[0][0]:
        return list(table[0][1 : 1 + columns])
    for a, b in itertools.pairwise(table):
        if u <= b[0]:
            span = b[0] - a[0]
            t = 0.0 if span <= 0 else (u - a[0]) / span
            return [a[1 + k] + (b[1 + k] - a[1 + k]) * t for k in range(columns)]
    return list(table[-1][1 : 1 + columns])


def _motion(raw: Any, where: str, scale: float, input_spec: dict[str, Any] | None, offset: float, pivot: Vec, copy_turn: Mat) -> tuple[Motion | None, Vec]:
    if raw is None:
        return None, pivot
    if not isinstance(raw, dict):
        raise SpecError(f"{where}.motion must be an object")
    if input_spec is None:
        raise SpecError(f"{where}.motion needs the spec's top-level 'input' (the one value that drives everything)")
    kind = raw.get("type")
    if kind not in MOTIONS:
        raise SpecError(f"{where}.motion.type must be one of {', '.join(MOTIONS)}")
    axis = _apply(copy_turn, _unit(_vec(raw.get("axis"), f"{where}.motion.axis", (0.0, 0.0, 1.0))))
    if raw.get("pivot") is not None:
        pivot = _mul(_vec(raw.get("pivot"), f"{where}.motion.pivot"), scale)
    table = raw.get("table")
    columns = {"rotate": 1, "slide": 1, "rigid": 4}[str(kind)]
    if table is not None:
        if not isinstance(table, list) or len(table) < 2 or not all(isinstance(r, list) and len(r) == columns + 1 for r in table):
            raise SpecError(
                f"{where}.motion.table must be rows of [input, {'angle' if kind == 'rotate' else 'mm' if kind == 'slide' else 'dx, dy, dz, angle'}]"
            )
        rows = sorted([[float(v) for v in r] for r in table], key=lambda r: r[0])
    elif kind == "rigid":
        raise SpecError(f"{where}.motion: a rigid motion needs a 'table'")
    else:
        rows = None
    lo, hi = float(input_spec["min"]), float(input_spec["max"])
    period = hi - lo
    periodic = bool(input_spec.get("periodic", True))
    translate: list[Vec] = []
    angle: list[float] = []
    for k in range(SAMPLES):
        u = lo + period * k / (SAMPLES - 1) + offset
        if rows is not None:
            if periodic and period > 0 and not (rows[0][0] <= u <= rows[-1][0]):
                u = lo + (u - lo) % period
            vals = _interp(rows, u, columns)
        elif kind == "rotate":
            vals = [_num(raw, "ratio", where, 1.0) * u + _num(raw, "offset", where, 0.0)]
        else:
            amp = _num(raw, "amplitude", where)
            vals = [amp * math.sin(math.radians(_num(raw, "ratio", where, 1.0) * u + _num(raw, "phase", where, 0.0)))]
        if kind == "rotate":
            translate.append((0.0, 0.0, 0.0))
            angle.append(vals[0])
        elif kind == "slide":
            translate.append(_mul(axis, vals[0] * scale))
            angle.append(0.0)
        else:
            translate.append(_apply(copy_turn, _mul((vals[0], vals[1], vals[2]), scale)))
            angle.append(vals[3])
    return Motion(axis=axis, translate=translate, angle=angle), pivot


def _expand(parts: list[Any]) -> list[tuple[dict[str, Any], int, Mat, Vec, float]]:
    """Each part with its copy index, copy rotation, copy offset and input offset."""
    out: list[tuple[dict[str, Any], int, Mat, Vec, float]] = []
    for k, raw in enumerate(parts):
        if not isinstance(raw, dict):
            raise SpecError(f"parts[{k}] must be an object")
        rep = raw.get("repeat")
        if rep is None:
            out.append((raw, -1, IDENTITY, (0.0, 0.0, 0.0), 0.0))
            continue
        if not isinstance(rep, dict):
            raise SpecError(f"parts[{k}].repeat must be an object")
        count = int(_num(rep, "count", f"parts[{k}].repeat", positive=True))
        if count > MAX_COPIES:
            raise SpecError(f"parts[{k}].repeat.count is above {MAX_COPIES}")
        axis = _vec(rep.get("axis"), f"parts[{k}].repeat.axis", (0.0, 0.0, 1.0))
        centre = _vec(rep.get("center"), f"parts[{k}].repeat.center", (0.0, 0.0, 0.0))
        step = _vec(rep.get("offset"), f"parts[{k}].repeat.offset", (0.0, 0.0, 0.0))
        total = float(rep.get("angle", 360.0 if not rep.get("offset") else 0.0))
        full = abs(abs(total) - 360.0) < 1e-9
        phase = float(rep.get("input_step", 0.0))
        for i in range(count):
            turn_deg = total * i / (count if full else max(1, count - 1)) if total else 0.0
            turn = axis_angle(axis, turn_deg)
            # p -> centre + turn (p - centre) + i * offset, written as turn p + shift
            shift = _add(_sub(centre, _apply(turn, centre)), _mul(step, i))
            out.append((raw, i, turn, shift, phase * i))
    return out


def load_spec(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("the spec must be a JSON object")
    return data


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_assembly(spec: dict[str, Any], base_dir: Path) -> Assembly:
    """Validate a spec and bake every part's mesh, explode and motion."""
    unit = spec.get("units", "mm")
    if unit not in UNITS:
        raise SpecError(f"'units' must be one of {', '.join(UNITS)}")
    scale = UNITS[unit]
    title = spec.get("title")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("'title' is required: name the assembly")
    raw_parts = spec.get("parts")
    if not isinstance(raw_parts, list) or not raw_parts:
        raise SpecError("'parts' must be a non-empty list")
    input_spec = spec.get("input")
    if input_spec is not None:
        if not isinstance(input_spec, dict):
            raise SpecError("'input' must be an object")
        lo = _num(input_spec, "min", "input", 0.0, positive=False)
        hi = _num(input_spec, "max", "input", 360.0, positive=False)
        if hi <= lo:
            raise SpecError("input: 'max' must be above 'min'")
        input_spec = {
            "name": str(input_spec.get("name", "Input")),
            "unit": str(input_spec.get("unit", "deg")),
            "min": lo,
            "max": hi,
            "default": _num(input_spec, "default", "input", lo, positive=False),
            "periodic": bool(input_spec.get("periodic", True)),
            "seconds": _num(input_spec, "seconds", "input", 6.0, positive=True),
        }
    subsystems = spec.get("subsystems") or []
    if not isinstance(subsystems, list):
        raise SpecError("'subsystems' must be a list")
    known: dict[str, dict[str, Any]] = {}
    for k, s in enumerate(subsystems):
        if not isinstance(s, dict) or not isinstance(s.get("id"), str):
            raise SpecError(f"subsystems[{k}] needs an 'id'")
        known[s["id"]] = {"id": s["id"], "name": str(s.get("name", s["id"])), "color": s.get("color"), "note": str(s.get("note", ""))}
    notes: list[str] = []
    parts: list[Part] = []
    seen: set[str] = set()
    for raw, copy, copy_turn, copy_shift, input_offset in _expand(raw_parts):
        base_id = raw.get("id")
        if not isinstance(base_id, str) or not base_id:
            raise SpecError("every part needs an 'id'")
        pid = base_id if copy < 0 else f"{base_id}-{copy + 1}"
        where = f"part '{pid}'"
        if pid in seen:
            raise SpecError(f"{where}: the id is used twice")
        seen.add(pid)
        name = str(raw.get("name", base_id)) + ("" if copy < 0 else f" {copy + 1}")
        subsystem = str(raw.get("subsystem", "assembly"))
        if subsystem not in known:
            if subsystems:
                raise SpecError(f"{where}: subsystem '{subsystem}' is not listed in 'subsystems'")
            known[subsystem] = {"id": subsystem, "name": subsystem.replace("-", " ").title(), "color": None, "note": ""}
        material = str(raw.get("material", "plastic"))
        if material not in MATERIALS:
            raise SpecError(f"{where}: material must be one of {', '.join(MATERIALS)}")
        shapes = raw.get("shapes") if raw.get("shapes") is not None else ([raw["shape"]] if raw.get("shape") else None)
        if not isinstance(shapes, list) or not shapes:
            raise SpecError(f"{where}: give 'shape' (one) or 'shapes' (several)")
        mesh = Mesh()
        for k, shape in enumerate(shapes):
            if not isinstance(shape, dict):
                raise SpecError(f"{where}: shapes[{k}] must be an object")
            mesh.extend(build_shape(shape, f"{where} shapes[{k}]", scale, base_dir))
        place_turn = _matmul(copy_turn, euler_xyz(_vec(raw.get("rotation"), f"{where}.rotation", (0.0, 0.0, 0.0))))
        place_at = _add(_apply(copy_turn, _mul(_vec(raw.get("position"), f"{where}.position", (0.0, 0.0, 0.0)), scale)), _mul(copy_shift, scale))
        world = mesh.transformed(place_turn, place_at)
        motion, pivot = _motion(raw.get("motion"), where, scale, input_spec, input_offset, place_at, copy_turn)
        if motion is not None and raw.get("motion", {}).get("pivot") is not None:
            pivot = _add(_apply(copy_turn, pivot), _mul(copy_shift, scale))
        local = world.transformed(IDENTITY, _mul(pivot, -1.0))
        if not raw.get("note"):
            notes.append(f"{where} has no 'note' saying what it does")
        explode = raw.get("explode") or {}
        if not isinstance(explode, dict):
            raise SpecError(f"{where}.explode must be an object")
        direction_raw = explode.get("direction")
        parts.append(
            Part(
                id=pid,
                name=name,
                subsystem=subsystem,
                material=material,
                color=raw.get("color"),
                note=str(raw.get("note", "")),
                accent=bool(raw.get("accent", False)),
                cutaway=bool(raw.get("cutaway", False)),
                pivot=pivot,
                mesh=local,
                explode_direction=_apply(copy_turn, _unit(_vec(direction_raw, f"{where}.explode.direction"))) if direction_raw is not None else (0.0, 0.0, 0.0),
                explode_distance=_num(explode, "distance", f"{where}.explode", -1.0, positive=False) * (scale if explode.get("distance") is not None else 1.0),
                explode_order=int(_num(explode, "order", f"{where}.explode", 0.0, positive=False)),
                motion=motion,
            )
        )
    for part in parts:
        a, b = part.mesh.bounds()
        part.centroid = _add(part.pivot, _mul(_add(a, b), 0.5))
    lo = [min(p.centroid[k] for p in parts) for k in range(3)]
    hi = [max(p.centroid[k] for p in parts) for k in range(3)]
    centre: Vec = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    stages = max(p.explode_order for p in parts) + 1
    assembly = Assembly(
        title=title.strip(),
        subtitle=str(spec.get("subtitle", "")),
        summary=str(spec.get("summary", "")),
        source=_as_dict(spec.get("source")),
        accent=str(spec.get("accent", "#d4552b")),
        background=str(spec.get("background", "#ecebe6")),
        subsystems=[known[k] for k in known],
        input=input_spec,
        steps=[],
        parts=parts,
        stages=stages,
        notes=notes,
        camera=_as_dict(spec.get("camera")),
    )
    (alo, ahi) = assembly.bounds(0.0)
    diagonal = _length(_sub(ahi, alo)) or 1.0
    for part in parts:
        if part.explode_direction == (0.0, 0.0, 0.0):
            part.explode_direction = _unit(_sub(part.centroid, centre))
        if part.explode_distance < 0:
            part.explode_distance = 0.35 * diagonal
    if not assembly.source:
        notes.append("no 'source': name the one reference the dimensions come from")
    ids = {p.id for p in parts} | {s["id"] for s in assembly.subsystems} | {str(r.get("id")) for r in raw_parts if isinstance(r, dict)}
    for k, step in enumerate(spec.get("steps") or []):
        if not isinstance(step, dict) or not step.get("title"):
            raise SpecError(f"steps[{k}] needs a 'title'")
        focus = step.get("focus") or []
        unknown = [f for f in focus if f not in ids]
        if unknown:
            raise SpecError(f"steps[{k}].focus names unknown parts or subsystems: {', '.join(unknown)}")
        assembly.steps.append(
            {
                "title": str(step["title"]),
                "text": str(step.get("text", "")),
                "explode": float(step.get("explode", 0.0)),
                "input": step.get("input"),
                "focus": sorted(focus_ids(assembly, focus)),
                "view": step.get("view"),
                "section": bool(step.get("section", False)),
            }
        )
    return assembly


def focus_ids(assembly: Assembly, focus: Iterable[str]) -> set[str]:
    """Part ids named directly, by subsystem, or by a repeated part's base id."""
    wanted = set(focus)
    return {p.id for p in assembly.parts if p.id in wanted or p.subsystem in wanted or p.id.rsplit("-", 1)[0] in wanted}


def overlaps(assembly: Assembly, explode: float, threshold: float = 0.25) -> list[tuple[str, str, float]]:
    """Pairs whose boxes still overlap by more than ``threshold`` of the smaller one."""
    boxes: list[tuple[str, Vec, Vec, float]] = []
    for p in assembly.parts:
        a, b = p.mesh.bounds()
        shift = _add(p.pivot, assembly.explode_offset(p, explode))
        lo, hi = _add(a, shift), _add(b, shift)
        vol = max(1e-9, (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2]))
        boxes.append((p.id, lo, hi, vol))
    found: list[tuple[str, str, float]] = []
    for i, (ia, la, ha, va) in enumerate(boxes):
        for ib, lb, hb, vb in boxes[i + 1 :]:
            d = [min(ha[k], hb[k]) - max(la[k], lb[k]) for k in range(3)]
            if min(d) <= 0:
                continue
            share = d[0] * d[1] * d[2] / min(va, vb)
            if share > threshold:
                found.append((ia, ib, share))
    return sorted(found, key=lambda x: -x[2])
