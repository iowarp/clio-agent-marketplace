"""Flow past an STL body: placement, grid, voxel mask and input.i3d.

The body case is Incompact3d's cylinder wake case (``itype = 5``) with the
clio geometry patch (the ``+clio`` variant of the ``clio.xcompact3d`` Spack
recipe): a uniform inflow along
+x, a convective outflow, periodic sides, and the body immersed through the
immersed boundary method from a voxel mask (``clio-geometry.txt`` and
``clio-geometry.bin``).

Lengths are in body lengths L (the STL's x extent unless a reference length is
given), so the body is scaled to L = 1, and the Reynolds number is U L / nu.
Pure Python, so a site needs nothing beyond jarvis-cd to configure a run.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Vec = tuple[float, float, float]
Triangle = tuple[Vec, Vec, Vec]

#: Point fields each body snapshot holds: the cylinder case's, plus ``ep`` (the body).
BODY_ARRAYS = ("ux", "uy", "uz", "pp", "vort", "critq", "ep")
#: Above this CFL number (U dt / dx) the case is refused; the tested cases run at 0.1.
CFL_LIMIT = 0.2
#: dt nu sum(1/dx^2) must stay below this with the hyperviscous second derivative
#: (isecondder = 5): 0.0077 ran and 0.013 diverged on a NACA 4412 section.
DIFFUSION_LIMIT = 0.0075


class CaseError(ValueError):
    """A body case that cannot run as asked, with the way forward in the message."""


# -- STL ---------------------------------------------------------------------


def read_stl(path: Path) -> list[Triangle]:
    """Triangles of a binary or ASCII STL file."""
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if count > 0 and 84 + 50 * count == len(data):
            triangles = []
            for index in range(count):
                values = struct.unpack_from("<12f", data, 84 + 50 * index)
                triangles.append(
                    (
                        (values[3], values[4], values[5]),
                        (values[6], values[7], values[8]),
                        (values[9], values[10], values[11]),
                    )
                )
            return triangles
    vertices = [
        tuple(float(x) for x in line.split()[1:4])
        for line in data.decode("ascii", errors="replace").splitlines()
        if line.strip().startswith("vertex")
    ]
    if not vertices or len(vertices) % 3:
        raise CaseError(f"{path} is neither a binary nor an ASCII STL file")
    return [tuple(vertices[i : i + 3]) for i in range(0, len(vertices), 3)]  # type: ignore[misc]


def write_stl(triangles: list[Triangle], path: Path) -> None:
    """Write a binary STL: the body as the solver sees it, for a viewer to draw."""
    with open(path, "wb") as out:
        out.write(b"clio_jarvis.xcompact3d body".ljust(80, b" "))
        out.write(struct.pack("<I", len(triangles)))
        for a, b, c in triangles:
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            out.write(struct.pack("<12fH", *(x / length for x in n), *a, *b, *c, 0))


def bounds(triangles: list[Triangle]) -> tuple[Vec, Vec]:
    xs = [p[0] for t in triangles for p in t]
    ys = [p[1] for t in triangles for p in t]
    zs = [p[2] for t in triangles for p in t]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def volume(triangles: list[Triangle]) -> float:
    total = 0.0
    for a, b, c in triangles:
        total += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return abs(total) / 6.0


def transform(triangles: list[Triangle], scale: float, turn_deg: float, shift: Vec) -> list[Triangle]:
    """Scale about the origin, turn about +z, then shift."""
    angle = math.radians(turn_deg)
    c, s = math.cos(angle), math.sin(angle)

    def move(p: Vec) -> Vec:
        x, y, z = p[0] * scale, p[1] * scale, p[2] * scale
        return (c * x - s * y + shift[0], s * x + c * y + shift[1], z + shift[2])

    return [(move(a), move(b), move(c_)) for a, b, c_ in triangles]


# -- voxel mask --------------------------------------------------------------


def voxelise(
    triangles: list[Triangle], origin: Vec, spacing: Vec, shape: tuple[int, int, int]
) -> bytearray:
    """Mark voxel centres inside a closed mesh by ray parity along +x; x fastest.

    Each (y, z) column casts one ray, nudged off the grid by an irrational
    fraction of a spacing so it never passes exactly through an edge or vertex.
    """
    nx, ny, nz = shape
    x0, y0, z0 = origin
    dx, dy, dz = spacing
    nudge_y = dy * 1e-6 * math.sqrt(2.0)
    nudge_z = dz * 1e-6 * math.sqrt(3.0)
    hits: dict[tuple[int, int], list[float]] = {}
    for a, b, c in triangles:
        j0 = max(0, math.ceil((min(a[1], b[1], c[1]) - y0 - nudge_y) / dy))
        j1 = min(ny - 1, math.floor((max(a[1], b[1], c[1]) - y0 - nudge_y) / dy))
        k0 = max(0, math.ceil((min(a[2], b[2], c[2]) - z0 - nudge_z) / dz))
        k1 = min(nz - 1, math.floor((max(a[2], b[2], c[2]) - z0 - nudge_z) / dz))
        if j0 > j1 or k0 > k1:
            continue
        v0y, v0z = b[1] - a[1], b[2] - a[2]
        v1y, v1z = c[1] - a[1], c[2] - a[2]
        det = v0y * v1z - v1y * v0z
        if det == 0.0:
            continue
        for k in range(k0, k1 + 1):
            wz = z0 + k * dz + nudge_z - a[2]
            for j in range(j0, j1 + 1):
                wy = y0 + j * dy + nudge_y - a[1]
                u = (wy * v1z - v1y * wz) / det
                v = (v0y * wz - wy * v0z) / det
                if u >= 0.0 and v >= 0.0 and u + v <= 1.0:
                    x = a[0] + u * (b[0] - a[0]) + v * (c[0] - a[0])
                    hits.setdefault((j, k), []).append(x)
    mask = bytearray(nx * ny * nz)
    for (j, k), xs in hits.items():
        xs.sort()
        row = (k * ny + j) * nx
        for enter, leave in zip(xs[0::2], xs[1::2]):
            i0 = max(0, math.ceil((enter - x0) / dx))
            i1 = min(nx - 1, math.floor((leave - x0) / dx))
            for i in range(i0, i1 + 1):
                mask[row + i] = 1
    return mask


@dataclass
class Mask:
    data: bytearray
    shape: tuple[int, int, int]
    origin: Vec
    spacing: Vec

    @property
    def solid(self) -> int:
        return sum(self.data)

    def write(self, run_dir: Path) -> None:
        nx, ny, nz = self.shape
        o, d = self.origin, self.spacing
        (run_dir / "clio-geometry.txt").write_text(
            f"{nx} {ny} {nz}\n{o[0]!r} {o[1]!r} {o[2]!r}\n{d[0]!r} {d[1]!r} {d[2]!r}\n",
            encoding="ascii",
        )
        (run_dir / "clio-geometry.bin").write_bytes(bytes(self.data))


def mask_for(
    triangles: list[Triangle], spacing: Vec, span: tuple[float, float] | None = None
) -> Mask:
    """Voxelise the body around its bounding box, on solver points.

    The mask origin is a multiple of the spacing, so voxel centres are solver
    points. With ``span`` (z0, z1) the body is a section extruded through a
    periodic span: its middle z-plane is voxelised once and repeated on every
    z-plane from z0 to z1.
    """
    lower, upper = bounds(triangles)

    def axis(i: int) -> tuple[float, int]:
        step = spacing[i]
        start = (math.floor(lower[i] / step) - 1) * step
        stop = (math.ceil(upper[i] / step) + 1) * step
        return start, round((stop - start) / step) + 1

    ox, nx = axis(0)
    oy, ny = axis(1)
    if span is None:
        oz, nz = axis(2)
        return Mask(voxelise(triangles, (ox, oy, oz), spacing, (nx, ny, nz)), (nx, ny, nz), (ox, oy, oz), spacing)
    middle = 0.5 * (lower[2] + upper[2])
    plane = voxelise(triangles, (ox, oy, middle), spacing, (nx, ny, 1))
    z0, z1 = span
    nz = round((z1 - z0) / spacing[2]) + 1
    return Mask(plane * nz, (nx, ny, nz), (ox, oy, z0), spacing)


# -- the case ----------------------------------------------------------------


def nice(n: int, periodic: bool) -> int:
    """Smallest count >= n whose FFT length (n, or n - 1 when not periodic) is 2^a 3^b 5^c."""
    n = max(n, 8)
    while True:
        m = n if periodic else n - 1
        for p in (2, 3, 5):
            while m % p == 0:
                m //= p
        if m == 1:
            return n
        n += 1


def nice_dt(limit: float) -> float:
    """The largest of 1, 1.5, 2, 2.5, 3, 4 or 5 times a power of ten at most ``limit``."""
    power = 10.0 ** math.floor(math.log10(limit))
    for factor in (5.0, 4.0, 3.0, 2.5, 2.0, 1.5, 1.0):
        if factor * power <= limit:
            return factor * power
    return power


def decomposition(nprocs: int, nx: int, ny: int, nz: int) -> tuple[int, int]:
    """The 2D pencil grid (p_row, p_col) closest to square that the grid allows."""
    best: tuple[int, int] | None = None
    for p_col in range(1, nprocs + 1):
        if nprocs % p_col:
            continue
        p_row = nprocs // p_col
        if p_row > min(nx, ny) or p_col > min(ny, nz):
            continue
        if best is None or max(p_row, p_col) < max(best):
            best = (p_row, p_col)
    if best is None:
        raise CaseError(f"{nprocs} MPI processes cannot split a {nx} x {ny} x {nz} grid; use fewer")
    return best


def span_mode(triangles: list[Triangle], requested: str) -> str:
    """``periodic`` for a section extruded along z (a wing section), else ``free``."""
    if requested != "auto":
        return requested
    lower, upper = bounds(triangles)
    size = [u - l for u, l in zip(upper, lower)]
    if size[2] <= 0.0:
        return "free"
    step = min(size[0], size[1]) / 100.0
    plane = mask_for(triangles, (step, step, step), span=(0.0, 0.0))
    area = plane.solid * step * step
    if area <= 0.0:
        return "free"
    prism = area * size[2]
    return "periodic" if abs(volume(triangles) - prism) <= 0.05 * prism else "free"


@dataclass
class BodyCase:
    """A sized body case: everything input.i3d, the mask and the view need."""

    span: str
    scale: float
    grid: tuple[int, int, int]
    domain: Vec
    spacing: Vec
    decomposition: tuple[int, int]
    force_volume: dict[str, float]
    body: list[Triangle]
    mask: Mask
    facts: dict[str, Any] = field(default_factory=dict)


def plan_body(
    stl: Path,
    *,
    resolution: int,
    angle: float,
    reference_length: float,
    span: str,
    upstream: float,
    downstream: float,
    lateral: float,
    nprocs: int,
    inflow: float,
    re: float,
    dt: float,
) -> BodyCase:
    raw = read_stl(stl)
    lower, upper = bounds(raw)
    reference = reference_length or (upper[0] - lower[0])
    if reference <= 0:
        raise CaseError("the body has no length along x; set reference_length")
    h = 1.0 / resolution
    # Angle of attack: nose up for flow along +x is a turn by -angle about +z.
    body = transform(raw, 1.0 / reference, -angle, (0.0, 0.0, 0.0))
    mode = span_mode(body, span)
    lower, upper = bounds(body)
    size = tuple(u - l for u, l in zip(upper, lower))

    nx = nice(math.ceil((upstream + size[0] + downstream) / h) + 1, False)
    ny = nice(math.ceil((size[1] + 2 * lateral) / h), True)
    if mode == "periodic":
        # An extruded section is close to 2D: twice the in-plane spacing across the span.
        nz = nice(max(8, round(size[2] / (2 * h))), True)
        zlz = size[2]
        dz = zlz / nz
    else:
        nz = nice(math.ceil((size[2] + 2 * lateral) / h), True)
        dz = h
        zlz = nz * h
    xlx, yly = (nx - 1) * h, ny * h

    shift = (
        upstream - lower[0],
        0.5 * yly - 0.5 * (lower[1] + upper[1]),
        -lower[2] if mode == "periodic" else 0.5 * zlz - 0.5 * (lower[2] + upper[2]),
    )
    body = transform(body, 1.0, 0.0, shift)
    mask = mask_for(body, (h, h, dz), span=(0.0, zlz - dz) if mode == "periodic" else None)
    solid = mask.solid
    if solid == 0:
        raise CaseError(
            f"no grid point falls inside the body at resolution {resolution}; raise resolution "
            "or check that the STL is a closed solid"
        )

    cfl = inflow * dt / h
    nu = inflow / re
    diffusion = dt * nu * (2.0 / (h * h) + 1.0 / (dz * dz))
    advice = nice_dt(min(0.1 * h / inflow, DIFFUSION_LIMIT / (nu * (2.0 / (h * h) + 1.0 / (dz * dz)))))
    if cfl > CFL_LIMIT or diffusion > DIFFUSION_LIMIT:
        raise CaseError(
            f"dt {dt:g} is unstable on this grid (CFL {cfl:.3f}, limit {CFL_LIMIT}; diffusion "
            f"number {diffusion:.4f}, limit {DIFFUSION_LIMIT}); use dt {advice:g} or less"
        )

    blower, bupper = bounds(body)
    margin = max(0.25, 4 * h)
    force = {
        "xld": max(blower[0] - margin, h),
        "xrd": min(bupper[0] + margin, xlx - h),
        "yld": max(blower[1] - margin, h),
        "yud": min(bupper[1] + margin, yly - h),
    }
    if mode == "free":
        force["zfr"] = max(blower[2] - margin, dz)
        force["zbk"] = min(bupper[2] + margin, zlz - dz)
    across = size[1] / h
    facts: dict[str, Any] = {
        "reference_length_stl": reference,
        "body_size": list(size),
        "body_lower": list(blower),
        "body_upper": list(bupper),
        "triangles": len(body),
        "solid_voxels": solid,
        "points_across_body": round(across, 1),
        "cfl": round(cfl, 4),
        "diffusion_number": round(diffusion, 5),
        "suggested_dt": advice,
    }
    if across < 6:
        facts["warning"] = (
            f"the body is {across:.1f} grid points thick across the flow; raise resolution "
            "for forces worth quoting"
        )
    return BodyCase(
        span=mode,
        scale=1.0 / reference,
        grid=(nx, ny, nz),
        domain=(xlx, yly, zlz),
        spacing=(h, h, dz),
        decomposition=decomposition(nprocs, nx, ny, nz),
        force_volume=force,
        body=body,
        mask=mask,
        facts=facts,
    )


def input_i3d(
    case: BodyCase,
    *,
    inflow: float,
    re: float,
    dt: float,
    ilast: int,
    ioutput: int,
    icheckpoint: int = 100000000,
    initstat: int = 100000000,
) -> str:
    nx, ny, nz = case.grid
    xlx, yly, zlz = case.domain
    f = case.force_volume
    volume_lines = [f"{key}(1) = {f[key]:.6f}" for key in ("xld", "xrd", "yld", "yud")]
    if case.span == "free":
        volume_lines += [f"zfr(1) = {f['zfr']:.6f}", f"zbk(1) = {f['zbk']:.6f}", "i2dsim = 0"]
    else:
        volume_lines.append("i2dsim = 1")
    newline = "\n"
    return f"""! -*- mode: f90 -*-
! Written by clio_jarvis.xcompact3d: flow along +x past the body in
! clio-geometry.txt and clio-geometry.bin (immersed boundary), lengths in body
! lengths L. Reynolds number U L / nu = {re:g}, so 1/nu = re / U below.

&BasicParam
itype = 5
p_row = {case.decomposition[0]}
p_col = {case.decomposition[1]}
nx = {nx}
ny = {ny}
nz = {nz}
istret = 0
beta = 0.259065151
xlx = {xlx:.10g}
yly = {yly:.10g}
zlz = {zlz:.10g}
nclx1 = 2
nclxn = 2
ncly1 = 0
nclyn = 0
nclz1 = 0
nclzn = 0
iin = 1
re = {re / inflow:.10g}
u1 = {inflow:.10g}
u2 = {inflow:.10g}
init_noise = 0.05
inflow_noise = 0.0
dt = {dt:.10g}
ifirst = 1
ilast = {ilast}
ilesmod = 0
iscalar = 0
iibm = 1
/End

&NumOptions
ifirstder = 4
isecondder = 5
ipinter = 3
itimescheme = 3
/End

&InOutParam
irestart = 0
icheckpoint = {icheckpoint}
ioutput = {ioutput}
ilist = {max(1, ioutput // 5)}
nvisu = 1
/End

&Statistics
nstat = 1
initstat = {initstat}
/End

&ScalarParam
numscalar = 0
Sc = 0.2
/End

&LESModel
jles = 0
smagcst = 0.14
SmagWallDamp = 1
walecst = 0.5
iconserv = 0
/End

&ibmstuff
cex = 0.
cey = 0.
ra = 0.
nraf = 10
nobjmax = 1
iforces = 1
nvol = 1
/End

&ForceCVs
{newline.join(volume_lines)}
/End

&CASE
/End
"""
