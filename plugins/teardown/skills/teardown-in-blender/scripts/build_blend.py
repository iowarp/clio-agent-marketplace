"""Build a teardown spec into a real Blender scene: a .blend, renders, and an optional film.

Inside Blender (a full install; the .blend then opens in the Blender app):
    blender -b --factory-startup --python build_blend.py -- SPEC.json --out DIR [options]
Or with the ``bpy`` module (render only, no Blender app; bpy 4.5 needs Python 3.11):
    uv run --no-project --python 3.11 --with bpy==4.5.* python build_blend.py SPEC.json --out DIR

The parts, explode offsets and motion come from the same ``teardown_geometry`` module the
browser page uses, so both views agree. In the .blend, the "Teardown" empty carries an
``explode`` property (0 assembled, 1 fully exploded) that drives every part, and the
timeline plays the mechanism through its input. Writes ``teardown.blend``,
``assembled.png``, ``exploded.png``, and with ``--animation`` ``teardown.mp4``; with
``--glb`` also ``teardown.glb``. Prints a JSON summary last.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy  # type: ignore[import-not-found]
from mathutils import Vector  # type: ignore[import-not-found]

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "exploded-teardown" / "scripts"))

import teardown_geometry as geo  # pyright: ignore[reportMissingImports]

MM = 0.001  # spec millimetres to Blender metres
FPS = 24
VIEWS = {"iso": (1.0, -1.45, 0.95), "front": (0.0, -1.0, 0.12), "side": (1.0, 0.0, 0.12), "top": (0.001, -0.02, 1.0), "back": (-0.8, 1.2, 0.6)}

# base colour (sRGB hex), metallic, roughness, coat, transmission
MATERIALS: dict[str, tuple[str, float, float, float, float]] = {
    "steel": ("#a9adb3", 1.0, 0.34, 0.0, 0.0),
    "aluminium": ("#c9ccd1", 1.0, 0.42, 0.0, 0.0),
    "cast-iron": ("#5b5e62", 0.75, 0.62, 0.0, 0.0),
    "brass": ("#cfa24a", 1.0, 0.32, 0.0, 0.0),
    "copper": ("#c4774a", 1.0, 0.3, 0.0, 0.0),
    "gold": ("#e3b54e", 1.0, 0.22, 0.0, 0.0),
    "chrome": ("#e4e6ea", 1.0, 0.08, 0.0, 0.0),
    "plastic": ("#3a3f45", 0.0, 0.48, 0.15, 0.0),
    "rubber": ("#232527", 0.0, 0.88, 0.0, 0.0),
    "glass": ("#dfeef2", 0.0, 0.04, 0.0, 1.0),
    "pcb": ("#1f6b45", 0.05, 0.5, 0.0, 0.0),
    "ceramic": ("#efece4", 0.0, 0.3, 0.4, 0.0),
    "wood": ("#a87a4f", 0.0, 0.7, 0.0, 0.0),
    "painted": ("#7d8a96", 0.1, 0.4, 0.3, 0.0),
}


def srgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def linear(hex_colour: str) -> tuple[float, float, float, float]:
    def one(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = srgb(hex_colour)
    return (one(r), one(g), one(b), 1.0)


def set_input(node: Any, names: tuple[str, ...], value: Any) -> None:
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return


def make_material(name: str, preset: str, colour: str | None) -> Any:
    base, metal, rough, coat, trans = MATERIALS[preset]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, ("Base Color",), linear(colour or base))
    # Solid viewport and Workbench film colour. Workbench adds no light lift, so the
    # display (sRGB) value keeps parts as light as in the Cycles stills.
    mat.diffuse_color = (*srgb(colour or base), 1.0)
    mat.metallic = min(metal, 0.6)
    mat.roughness = rough
    set_input(bsdf, ("Metallic",), metal)
    set_input(bsdf, ("Roughness",), rough)
    set_input(bsdf, ("Coat Weight", "Clearcoat"), coat)
    set_input(bsdf, ("Transmission Weight", "Transmission"), trans)
    if trans:
        set_input(bsdf, ("IOR",), 1.5)
    return mat


def make_mesh(part: geo.Part) -> Any:
    m = part.mesh
    verts = [(m.positions[i] * MM, m.positions[i + 1] * MM, m.positions[i + 2] * MM) for i in range(0, len(m.positions), 3)]
    faces = [tuple(m.indices[i : i + 3]) for i in range(0, len(m.indices), 3)]
    me = bpy.data.meshes.new(part.id)
    me.from_pydata(verts, [], faces)
    me.validate(clean_customdata=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "use_auto_smooth"):
        me.use_auto_smooth = True  # Blender before 4.1 needs it for custom normals
    normals = [(m.normals[i], m.normals[i + 1], m.normals[i + 2]) for i in range(0, len(m.normals), 3)]
    with contextlib.suppress(AttributeError, RuntimeError, TypeError):
        me.normals_split_custom_set_from_vertices(normals)
    me.update()
    return me


def explode_driver(obj: Any, control: Any, part: geo.Part, stages: int) -> None:
    clamp = f"min(max(e*{stages}-{part.explode_order},0),1)"
    for axis in range(3):
        d = part.explode_direction[axis] * part.explode_distance * MM
        if abs(d) < 1e-9:
            continue
        curve = obj.driver_add("delta_location", axis)
        drv = curve.driver
        drv.type = "SCRIPTED"
        var = drv.variables.new()
        var.name = "e"
        var.type = "SINGLE_PROP"
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = control
        var.targets[0].data_path = '["explode"]'
        drv.expression = f"{d:.6f}*{clamp}*{clamp}*(3-2*{clamp})"


def look_at(obj: Any, target: Vector) -> None:
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (target - obj.location).to_track_quat("-Z", "Y")


def world_points(scene: Any, control: Any, objects: dict[str, Any], explode: float, frame: int = 1) -> list[Vector]:
    """Evaluated world-space vertices of every part at one explode amount (subsampled)."""
    control["explode"] = float(explode)
    control.update_tag()
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    points: list[Vector] = []
    for obj in objects.values():
        ev = obj.evaluated_get(dg)
        verts = ev.data.vertices
        step = max(1, len(verts) // 400)
        mw = ev.matrix_world
        points.extend(mw @ verts[i].co for i in range(0, len(verts), step))
    return points


def frame_points(scene: Any, points: list[Vector], direction: Vector, fill: float = 0.86) -> tuple[Vector, float]:
    """Target and distance for a 50 mm camera on ``direction`` so ``points`` fill ``fill`` of the frame."""
    forward = -direction.normalized()
    rot = forward.to_track_quat("-Z", "Y")
    inv = rot.inverted()
    aspect = scene.render.resolution_x / scene.render.resolution_y
    tan_h = 18 / 50 * fill if aspect >= 1 else 18 / 50 * aspect * fill
    tan_v = tan_h / aspect
    local = [inv @ p for p in points]
    cx = (min(v.x for v in local) + max(v.x for v in local)) / 2
    cy = (min(v.y for v in local) + max(v.y for v in local)) / 2
    cz = (min(v.z for v in local) + max(v.z for v in local)) / 2
    distance = max(max(v.z - cz + abs(v.x - cx) / tan_h, v.z - cz + abs(v.y - cy) / tan_v) for v in local)
    return rot @ Vector((cx, cy, cz)), max(distance, 1e-3)


def fit_camera(scene: Any, points: list[Vector], direction: tuple[float, float, float], name: str) -> Any:
    target, distance = frame_points(scene, points, Vector(direction))
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 50
    cam_data.sensor_width = 36
    cam_data.sensor_fit = "AUTO"
    cam_data.clip_start = distance * 0.01
    cam_data.clip_end = distance * 20
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = target + Vector(direction).normalized() * distance
    look_at(cam, target)
    return cam


def orbit_camera(
    scene: Any,
    states: list[list[Vector]],
    direction: tuple[float, float, float],
    start: int,
    end: int,
    ramp: tuple[int, int],
    swing: float = 0.8,
) -> Any:
    """A film camera that swings ``swing`` radians around the vertical axis and keeps the parts
    framed while they explode. ``states`` are the part points at evenly spaced explode amounts
    (first assembled, last exploded); the explode runs linearly over the ``ramp`` frames."""
    d = Vector(direction).normalized()
    cam = fit_camera(scene, states[-1], tuple(d), "Camera film")
    angles = [swing * k / 8 for k in range(9)]

    def turned(a: float) -> Vector:
        return Vector((d.x * math.cos(a) - d.y * math.sin(a), d.x * math.sin(a) + d.y * math.cos(a), d.z))

    fits = [[frame_points(scene, pts, turned(a)) for a in angles] for pts in states]
    distances = [max(f[1] for f in fit) for fit in fits]
    targets = [fit[0][0] for fit in fits]
    # never pull in again once pulled back
    for k in range(1, len(distances)):
        distances[k] = max(distances[k], distances[k - 1])
    last = len(states) - 1
    cam.rotation_mode = "QUATERNION"
    for frame in range(start, end + 1, 2):
        t = (frame - start) / max(1, end - start)
        a = swing * (0.5 - 0.5 * math.cos(math.pi * t))
        e = min(max((frame - ramp[0]) / max(1, ramp[1] - ramp[0]), 0.0), 1.0) * last
        k = min(int(e), last - 1) if last else 0
        u = e - k if last else 0.0
        k1 = min(k + 1, last)
        target = targets[k].lerp(targets[k1], u)
        cam.location = target + turned(a) * (distances[k] + (distances[k1] - distances[k]) * u)
        look_at(cam, target)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_quaternion", frame=frame)
    cam.data.clip_start = distances[0] * 0.01
    cam.data.clip_end = distances[-1] * 20
    return cam


def studio(scene: Any, assembly: geo.Assembly, engine: str) -> None:
    lo0, hi0 = assembly.bounds(0.0)
    lo1, hi1 = assembly.bounds(1.0)
    lo = [min(lo0[k], lo1[k]) for k in range(3)]
    hi = [max(hi0[k], hi1[k]) for k in range(3)]
    centre = Vector([(lo[k] + hi[k]) / 2 * MM for k in range(3)])
    r = max(0.5 * math.dist(lo, hi) * MM, 1e-4)
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = linear(assembly.background)
        bg.inputs["Strength"].default_value = 0.55
    scene.world = world
    for name, offset, power, size in (
        # W per m^2 of light-to-subject distance, so exposure is the same at any scale
        ("Key", (-1.2, -1.6, 3.0), 14.0, 1.6),
        ("Fill", (2.2, -2.0, 0.8), 4.0, 2.2),
        ("Rim", (2.0, 2.5, 1.2), 8.0, 1.0),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.shape = "DISK"
        light.size = size * r
        position = centre + Vector(offset) * r
        light.energy = power * (position - centre).length_squared
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        look_at(obj, centre)
    gz = lo[2] * MM - 0.01 * r
    half = 20 * r
    plane = bpy.data.meshes.new("Ground")
    plane.from_pydata(
        [
            (centre.x - half, centre.y - half, gz),
            (centre.x + half, centre.y - half, gz),
            (centre.x + half, centre.y + half, gz),
            (centre.x - half, centre.y + half, gz),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    ground = bpy.data.objects.new("Ground", plane)
    scene.collection.objects.link(ground)
    mat = bpy.data.materials.new("Ground")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, ("Base Color",), linear(assembly.background))
    set_input(bsdf, ("Roughness",), 1.0)
    ground.data.materials.append(mat)
    if engine == "CYCLES":
        ground.is_shadow_catcher = True


def pick_engine(scene: Any, wanted: str) -> str:
    items = [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items]
    if wanted == "eevee":
        for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            if name in items:
                return name
    return "CYCLES"


def configure(scene: Any, engine: str, samples: int, width: int, height: int) -> None:
    scene.render.engine = engine
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 8
        scene.cycles.transmission_bounces = 8
    elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    views = [v.name for v in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in views else "Filmic"


def flatten(path: Path, background: str) -> None:
    """Composite a transparent render (parts plus caught shadow) onto the page colour."""
    import numpy as np  # pyright: ignore[reportMissingImports]  # bundled with Blender and bpy

    img = bpy.data.images.load(str(path))
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    a = px[:, 3:4]
    bg = np.array(srgb(background), dtype=np.float32)
    px[:, :3] = px[:, :3] * a + bg * (1 - a)
    px[:, 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def render_still(scene: Any, camera: Any, path: Path, background: str, transparent: bool) -> None:
    scene.camera = camera
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if transparent:
        flatten(path, background)


def key_motion(assembly: geo.Assembly, objects: dict[str, Any], start: int, cycle_frames: int, cycles: int) -> None:
    periodic = bool(assembly.input and assembly.input.get("periodic", True))
    count = geo.SAMPLES - 1
    for part in assembly.parts:
        if part.motion is None:
            continue
        obj = objects[part.id]
        m = part.motion
        turn = m.angle[-1] - m.angle[0] if periodic else 0.0
        shift = [m.translate[-1][k] - m.translate[0][k] for k in range(3)] if periodic else [0.0, 0.0, 0.0]
        for c in range(cycles):
            last = count + 1 if c == cycles - 1 else count
            for k in range(last):
                frame = start + c * cycle_frames + k * cycle_frames / count
                angle = m.angle[k] + c * turn
                t = [m.translate[k][j] + c * shift[j] for j in range(3)]
                obj.rotation_axis_angle = (math.radians(angle), *m.axis)
                obj.location = [(part.pivot[j] + t[j]) * MM for j in range(3)]
                obj.keyframe_insert("rotation_axis_angle", frame=frame)
                obj.keyframe_insert("location", frame=frame)


def workbench_look(scene: Any, background: str) -> None:
    """Fast, clean Workbench shading for the film: material colours, cavity, no ground."""
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.view_settings.view_transform = "Standard"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_object_outline = False
    shading.background_type = "WORLD"
    if scene.world is not None:
        scene.world.color = linear(background)[:3]
    scene.display.render_aa = "8"
    ground = bpy.data.objects.get("Ground")
    if ground is not None:
        ground.hide_render = True


def render_film(scene: Any, camera: Any, out: Path, background: str, film_engine: str) -> str:
    scene.camera = camera
    scene.render.film_transparent = False
    if film_engine == "workbench":
        workbench_look(scene, background)
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"  # Blender 5 splits still and video formats
    try:
        settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "HIGH"
        scene.render.filepath = str(out / "teardown.mp4")
        bpy.ops.render.render(animation=True)
        return str(out / "teardown.mp4")
    except (TypeError, RuntimeError):
        if hasattr(settings, "media_type"):
            settings.media_type = "IMAGE"
        settings.file_format = "PNG"
        (out / "frames").mkdir(exist_ok=True)
        scene.render.filepath = str(out / "frames" / "frame_")
        bpy.ops.render.render(animation=True)
        return str(out / "frames")


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Build a teardown spec in Blender")
    parser.add_argument("spec")
    parser.add_argument("--out", required=True, help="folder for the .blend, renders and film")
    parser.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--view", default=None, help="iso, front, side, top or back (default: the spec's camera)")
    parser.add_argument("--animation", action="store_true", help="also render a film: run, explode, run, with a slow camera swing")
    parser.add_argument("--film-engine", choices=("workbench", "render"), default="workbench", help="workbench (fast, default) or the stills engine")
    parser.add_argument("--glb", action="store_true", help="also export teardown.glb")
    parser.add_argument("--no-render", action="store_true", help="only build and save the .blend")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        assembly = geo.build_assembly(geo.load_spec(spec_path), spec_path.parent)
    except geo.SpecError as exc:
        print(f"spec error: {exc}", file=sys.stderr)
        return 2

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    scene = bpy.context.scene
    engine = pick_engine(scene, args.engine)
    configure(scene, engine, args.samples, args.width, args.height)

    control = bpy.data.objects.new("Teardown", None)
    control.empty_display_type = "PLAIN_AXES"
    scene.collection.objects.link(control)
    control["explode"] = 0.0
    control.id_properties_ui("explode").update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description="0 assembled, 1 fully exploded")
    control["title"] = assembly.title

    collections: dict[str, Any] = {}
    for sub in assembly.subsystems:
        coll = bpy.data.collections.new(sub["name"])
        scene.collection.children.link(coll)
        collections[sub["id"]] = coll
    materials: dict[tuple[str, str | None], Any] = {}
    objects: dict[str, Any] = {}
    for part in assembly.parts:
        colour = part.color or (assembly.accent if part.accent else None)
        key = (part.material, colour)
        if key not in materials:
            materials[key] = make_material(f"{part.material} {colour or ''}".strip(), part.material, colour)
        obj = bpy.data.objects.new(part.name, make_mesh(part))
        obj.data.materials.append(materials[key])
        obj.location = [v * MM for v in part.pivot]
        obj.rotation_mode = "AXIS_ANGLE"
        if part.motion is not None:
            obj.rotation_axis_angle = (0.0, *part.motion.axis)
        obj["part_id"] = part.id
        obj["subsystem"] = part.subsystem
        if part.note:
            obj["note"] = part.note
        collections[part.subsystem].objects.link(obj)
        explode_driver(obj, control, part, assembly.stages)
        objects[part.id] = obj

    studio(scene, assembly, engine)
    view = args.view or (assembly.camera.get("view") if isinstance(assembly.camera.get("view"), str) else None)
    direction = tuple(assembly.camera["direction"]) if isinstance(assembly.camera.get("direction"), list) else VIEWS.get(view or "iso", VIEWS["iso"])
    points_assembled = world_points(scene, control, objects, 0.0)
    points_exploded = world_points(scene, control, objects, 1.0)
    control["explode"] = 0.0
    cam_assembled = fit_camera(scene, points_assembled, direction, "Camera assembled")
    cam_exploded = fit_camera(scene, points_exploded, direction, "Camera exploded")

    seconds = float(assembly.input["seconds"]) if assembly.input else 4.0
    cycle_frames = max(24, round(seconds * FPS))
    cycles = 3 if args.animation else 1
    key_motion(assembly, objects, 1, cycle_frames, cycles)
    scene.frame_start = 1
    scene.frame_end = 1 + cycle_frames * cycles
    scene.frame_set(1)
    ramp = (1 + cycle_frames, 1 + 2 * cycle_frames)
    cam_film = None
    if args.animation:
        states = [world_points(scene, control, objects, k / 8) for k in range(9)]
        control["explode"] = 0.0
        control.update_tag()
        scene.frame_set(1)
        cam_film = orbit_camera(scene, states, direction, scene.frame_start, scene.frame_end, ramp)

    result: dict[str, Any] = {"engine": engine, "blender": bpy.app.version_string, "parts": len(assembly.parts), "triangles": assembly.triangle_count()}
    transparent = engine == "CYCLES"
    if not args.no_render:
        render_still(scene, cam_assembled, out / "assembled.png", assembly.background, transparent)
        control["explode"] = 1.0
        scene.frame_set(1)
        render_still(scene, cam_exploded, out / "exploded.png", assembly.background, transparent)
        result["assembled"] = str(out / "assembled.png")
        result["exploded"] = str(out / "exploded.png")
    control["explode"] = 0.0
    if args.animation:
        control.keyframe_insert('["explode"]', frame=1 + cycle_frames)
        control["explode"] = 1.0
        control.keyframe_insert('["explode"]', frame=1 + 2 * cycle_frames)
        if not args.no_render and cam_film is not None:
            result["film"] = render_film(scene, cam_film, out, assembly.background, args.film_engine)
            result["film_engine"] = scene.render.engine
            configure(scene, engine, args.samples, args.width, args.height)
            ground = bpy.data.objects.get("Ground")
            if ground is not None:
                ground.hide_render = False
        control["explode"] = 0.0
    scene.render.film_transparent = False
    scene.camera = cam_exploded
    scene.frame_set(1)
    notes = bpy.data.texts.new("START HERE")
    notes.write(
        f"{assembly.title}\n\n"
        "Select the 'Teardown' empty in the Outliner, then Object Properties > Custom Properties:\n"
        "set 'explode' to 0 (assembled) or 1 (fully exploded). Press Space to play the mechanism.\n"
        "Parts are grouped into one collection per subsystem; each part carries its id and note.\n"
        "Cameras: 'Camera assembled', 'Camera exploded'" + (", 'Camera film'" if cam_film is not None else "") + ".\n"
    )
    if args.glb:
        bpy.ops.export_scene.gltf(filepath=str(out / "teardown.glb"), export_format="GLB", export_animations=True)
        result["glb"] = str(out / "teardown.glb")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "teardown.blend"))
    result["blend"] = str(out / "teardown.blend")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
