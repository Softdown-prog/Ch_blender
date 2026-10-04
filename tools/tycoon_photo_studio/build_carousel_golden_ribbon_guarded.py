"""Fresh standalone City Horizon Golden Ribbon carousel builder.

This file intentionally does NOT import or inherit any previous City Horizon carousel
builder (classic/v3/v4/v5/Sunburst).  The supplied classic tycoon screenshot is used
only for broad category/color language: open carousel, visible mounts, and a bright
striped roof.  All geometry below is authored from primitives in this file.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CH_BLENDER = REPO_ROOT / "tools" / "ch_blender"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(CH_BLENDER) not in sys.path:
    sys.path.insert(0, str(CH_BLENDER))

import build_scene as bs  # noqa: E402
import scene_gate  # noqa: E402


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--recipe", required=True)
    p.add_argument("--studio-preset", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--save-blend", default=None)
    p.add_argument("--stage", choices=("preflight", "proxy"), default="preflight")
    p.add_argument("--preflight-profile", default=None)
    return p.parse_args(argv)


def _save_blend(path):
    if not path:
        return
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(target))


def _empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.rotation_mode = "XYZ"
    if parent is not None:
        obj.parent = parent
    return obj


def _mat(name, spec):
    return bs.make_material(
        f"GoldenRibbon_{name}",
        spec["rgba"],
        float(spec.get("roughness", 0.72)),
        float(spec.get("metallic", 0.0)),
        recipe=spec.get("recipe"),
        seed=int(spec.get("seed", 0)),
        strength=float(spec.get("strength", 1.0)),
    )


def _cube(name, parent, location, scale, material, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.scale = tuple(scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        mod = obj.modifiers.new(name="SoftEdges", type="BEVEL")
        mod.width = bevel
        mod.segments = 2
    obj.data.materials.append(material)
    return obj


def _cylinder(name, parent, location, radius, depth, material, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.data.materials.append(material)
    return obj


def _cone(name, parent, location, radius1, radius2, depth, material, vertices=12):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.data.materials.append(material)
    return obj


def _sphere(name, parent, location, scale, material, segments=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.scale = tuple(scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def _torus(name, parent, location, major_radius, minor_radius, material):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=64,
        minor_segments=8,
        location=(0.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.data.materials.append(material)
    return obj


def _cylinder_between(name, parent, start, end, radius, material, vertices=14):
    a = Vector(start)
    b = Vector(end)
    delta = b - a
    length = delta.length
    if length <= 1e-6:
        raise RuntimeError(f"Cannot create zero-length cylinder {name}")
    obj = _cylinder(name, parent, (0.0, 0.0, 0.0), radius, length, material, vertices)
    obj.location = (a + b) * 0.5
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    return obj


def _annular_sector(name, parent, a0, a1, r_inner, r_outer, z0, z1, material):
    pts = []
    for z in (z0, z1):
        pts.extend([
            (r_inner * math.cos(a0), r_inner * math.sin(a0), z),
            (r_inner * math.cos(a1), r_inner * math.sin(a1), z),
            (r_outer * math.cos(a1), r_outer * math.sin(a1), z),
            (r_outer * math.cos(a0), r_outer * math.sin(a0), z),
        ])
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(pts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(material)
    return obj


def _roof_gore(name, parent, a0, a1, r_inner, r_outer, inner_z, outer_z, thickness, material):
    top = [
        (r_inner * math.cos(a0), r_inner * math.sin(a0), inner_z),
        (r_inner * math.cos(a1), r_inner * math.sin(a1), inner_z),
        (r_outer * math.cos(a1), r_outer * math.sin(a1), outer_z),
        (r_outer * math.cos(a0), r_outer * math.sin(a0), outer_z),
    ]
    bottom = [(x, y, z - thickness) for x, y, z in top]
    verts = top + bottom
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(material)
    return obj


def _mark(obj, layer):
    obj["runtimeLayer"] = layer
    return obj


def _build_mount(index, rotor, angle, radius, mats, geo, frame_start, loop_frame):
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    pole_bottom = float(geo["platformTopZ"]) + 0.04
    pole_top = float(geo["canopyOuterZ"]) - 0.06
    _mark(_cylinder(
        f"GoldenPole_{index:02d}", rotor,
        (x, y, (pole_bottom + pole_top) * 0.5),
        0.034, pole_top - pole_bottom, mats["brass"], vertices=12
    ), "motion_overlay")

    mount = _empty(f"GoldenMount_{index:02d}", rotor)
    mount.location = (x, y, 0.0)
    mount.rotation_euler[2] = angle + math.pi * 0.5

    z = float(geo["horseBodyZ"])
    horse_palette = [mats["horse_white"], mats["horse_chestnut"], mats["horse_gray"], mats["horse_black"]]
    body_mat = horse_palette[index % len(horse_palette)]
    tack = mats["crimson"] if index % 2 == 0 else mats["jade"]
    mane = mats["dark"] if index % 3 else mats["brass"]

    pieces = []
    pieces.append(_sphere(f"GoldenHorseBody_{index:02d}", mount, (0.00, 0.0, z), (0.48, 0.18, 0.23), body_mat, 22, 12))
    pieces.append(_sphere(f"GoldenHorseChest_{index:02d}", mount, (0.34, 0.0, z + 0.12), (0.20, 0.15, 0.25), body_mat, 20, 11))
    neck = _sphere(f"GoldenHorseNeck_{index:02d}", mount, (0.42, 0.0, z + 0.34), (0.13, 0.12, 0.34), body_mat, 20, 11)
    neck.rotation_euler[1] = math.radians(-18.0)
    pieces.append(neck)
    head = _sphere(f"GoldenHorseHead_{index:02d}", mount, (0.61, 0.0, z + 0.55), (0.22, 0.13, 0.145), body_mat, 20, 11)
    head.rotation_euler[1] = math.radians(-7.0)
    pieces.append(head)
    pieces.append(_sphere(f"GoldenHorseMuzzle_{index:02d}", mount, (0.78, 0.0, z + 0.50), (0.12, 0.095, 0.085), body_mat, 16, 8))

    for ear_n, yy in enumerate((-0.065, 0.065)):
        ear = _cube(f"GoldenHorseEar_{index:02d}_{ear_n}", mount, (0.56, yy, z + 0.72), (0.035, 0.025, 0.085), body_mat, bevel=0.012)
        ear.rotation_euler[1] = math.radians(-14.0)
        pieces.append(ear)

    # Distinctive arched mane beads rather than the old three-block mane treatment.
    for bead in range(5):
        pieces.append(_sphere(
            f"GoldenHorseMane_{index:02d}_{bead}", mount,
            ((0.28 + 0.055 * bead), 0.0, z + 0.28 + 0.075 * bead),
            (0.060, 0.050, 0.070), mane, 12, 7
        ))

    pieces.append(_cube(f"GoldenHorseBlanket_{index:02d}", mount, (-0.04, 0.0, z + 0.18), (0.28, 0.20, 0.030), tack, bevel=0.025))
    pieces.append(_cube(f"GoldenHorseSaddle_{index:02d}", mount, (0.02, 0.0, z + 0.25), (0.19, 0.17, 0.045), mats["wine"], bevel=0.030))
    pieces.append(_cube(f"GoldenHorseBridle_{index:02d}", mount, (0.64, 0.0, z + 0.55), (0.070, 0.14, 0.025), tack, bevel=0.010))

    pose = 1.0 if index % 2 == 0 else -1.0
    legs = [
        ((0.27, -0.11, z - 0.10), (0.54, -0.11, z - 0.46 - 0.06 * pose)),
        ((0.18,  0.11, z - 0.11), (-0.02, 0.11, z - 0.50 + 0.05 * pose)),
        ((-0.25,-0.11, z - 0.09), (-0.52,-0.11, z - 0.40 + 0.04 * pose)),
        ((-0.20, 0.11, z - 0.09), (-0.02, 0.11, z - 0.52 - 0.04 * pose)),
    ]
    for leg_n, (start, end) in enumerate(legs):
        pieces.append(_cylinder_between(f"GoldenHorseLeg_{index:02d}_{leg_n}", mount, start, end, 0.045, body_mat, 10))
        pieces.append(_sphere(f"GoldenHorseHoof_{index:02d}_{leg_n}", mount, end, (0.070, 0.060, 0.050), mats["dark"], 12, 7))

    tail_a = _cylinder_between(f"GoldenHorseTailA_{index:02d}", mount, (-0.42, 0.0, z + 0.03), (-0.62, 0.0, z + 0.10), 0.050, mane, 10)
    tail_b = _cylinder_between(f"GoldenHorseTailB_{index:02d}", mount, (-0.62, 0.0, z + 0.10), (-0.75, 0.0, z - 0.08), 0.060, mane, 10)
    pieces.extend((tail_a, tail_b))

    for piece in pieces:
        _mark(piece, "motion_overlay")

    # Four-phase gentle vertical motion.  Frame 49 closes the loop, while frames 1..48 are unique exports.
    phase = (index % 4) / 4.0
    base_z = mount.location.z
    for frame in (frame_start, 13, 25, 37, loop_frame):
        t = (frame - frame_start) / float(loop_frame - frame_start)
        mount.location.z = base_z + 0.085 * math.sin(2.0 * math.pi * (t + phase))
        mount.keyframe_insert(data_path="location", index=2, frame=frame)
    mount.location.z = base_z


def build_scene(recipe, studio, out):
    bs.clear_scene()
    source_res = tuple(map(int, studio["render"]["sourceResolution"]))
    scene = bs.configure_scene(studio, source_res, str(out))
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    mats = {key: _mat(key, spec) for key, spec in recipe["materials"].items()}
    geo = recipe["geometry"]

    root = _empty("AssetRoot")
    root["assetId"] = recipe["assetId"]
    root["assetType"] = "animated_attraction"
    root["styleContract"] = recipe.get("styleContract", "CH_STYLIZED_PRERENDER_V1")
    root["cameraContract"] = "CH_CAMERA_V1"
    root["studioPreset"] = "CH_TYCOON_STUDIO_V1"
    root["runtimeRepresentation"] = "2D_RGBA_pre_rendered_sprite"
    root["directionPolicy"] = "rotate_asset_root_keep_camera_lights_fixed"
    root["qualityGateContract"] = "CH_SCENE_PREFLIGHT_V1"
    root["freshBuildPolicy"] = "standalone_no_previous_carousel_builder_inheritance"
    fp = recipe["footprint"]
    root["footprint"] = f"{fp['widthTiles']}x{fp['depthTiles']}"

    base_r = float(geo["baseRadius"])
    foundation = _cylinder("GoldenFoundation", root, (0.0, 0.0, 0.14), base_r, 0.28, mats["wine"], vertices=72)
    _mark(foundation, "static_base")
    scene_gate.tag(foundation, "attraction.foundation", ground_contact=True)

    apron_segments = int(geo["apronSegments"])
    for i in range(apron_segments):
        a0 = 2.0 * math.pi * i / apron_segments
        a1 = 2.0 * math.pi * (i + 1) / apron_segments
        mat = mats["crimson"] if i % 2 == 0 else mats["sunflower"]
        panel = _annular_sector(f"GoldenApron_{i:02d}", root, a0, a1, base_r - 0.34, base_r + 0.02, 0.22, 0.55, mat)
        _mark(panel, "static_base")

    med_count = int(geo.get("apronMedallionCount", 9))
    for i in range(med_count):
        a = 2.0 * math.pi * (i + 0.5) / med_count
        r = base_r + 0.04
        med = _sphere(f"GoldenApronMedallion_{i:02d}", root, (r * math.cos(a), r * math.sin(a), 0.40), (0.105, 0.105, 0.105), mats["jade"], 14, 8)
        _mark(med, "static_base")

    rotor = _empty("GoldenRibbonRotor", root)
    rotor["runtimeLayer"] = "motion_overlay"

    platform_r = float(geo["platformRadius"])
    platform_z = float(geo["platformTopZ"])
    _mark(_cylinder("GoldenPlatform", rotor, (0.0, 0.0, platform_z - 0.075), platform_r, 0.15, mats["wood"], vertices=72), "motion_overlay")
    _mark(_torus("GoldenPlatformOuterBrass", rotor, (0.0, 0.0, platform_z + 0.010), platform_r, 0.040, mats["brass"]), "motion_overlay")
    _mark(_torus("GoldenPlatformInnerJade", rotor, (0.0, 0.0, platform_z + 0.018), platform_r - 0.48, 0.025, mats["jade"]), "motion_overlay")

    # Original octagonal center kiosk, separate from any previous CH carousel center drum.
    kiosk_r = float(geo["centerKioskRadius"])
    kiosk_h = float(geo["centerKioskHeight"])
    kiosk_z = platform_z + 0.52
    _mark(_cylinder("GoldenCenterKiosk", rotor, (0.0, 0.0, kiosk_z), kiosk_r, kiosk_h, mats["wine"], vertices=8), "motion_overlay")
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        r = kiosk_r + 0.025
        panel = _cube(
            f"GoldenCenterPanel_{i:02d}", rotor,
            (r * math.cos(a), r * math.sin(a), kiosk_z),
            (0.035, 0.16, kiosk_h * 0.30),
            mats["jade"] if i % 2 == 0 else mats["ivory"], bevel=0.020
        )
        panel.rotation_euler[2] = a
        _mark(panel, "motion_overlay")
    _mark(_torus("GoldenCenterLowerBand", rotor, (0.0, 0.0, kiosk_z - kiosk_h * 0.48), kiosk_r, 0.030, mats["brass"]), "motion_overlay")
    _mark(_torus("GoldenCenterUpperBand", rotor, (0.0, 0.0, kiosk_z + kiosk_h * 0.48), kiosk_r, 0.030, mats["brass"]), "motion_overlay")

    canopy_r = float(geo["canopyRadius"])
    canopy_inner = float(geo["canopyInnerRadius"])
    outer_z = float(geo["canopyOuterZ"])
    inner_z = float(geo["canopyInnerZ"])
    thickness = float(geo["canopyThickness"])
    sectors = int(geo["canopySegments"])
    for i in range(sectors):
        a0 = 2.0 * math.pi * i / sectors
        a1 = 2.0 * math.pi * (i + 1) / sectors
        mat = mats["sunflower"] if i % 2 == 0 else mats["ivory"]
        gore = _roof_gore(f"GoldenRoofGore_{i:02d}", rotor, a0, a1, canopy_inner, canopy_r, inner_z, outer_z, thickness, mat)
        _mark(gore, "motion_overlay")

    _mark(_torus("GoldenCanopyOuterBrass", rotor, (0.0, 0.0, outer_z - 0.015), canopy_r, 0.060, mats["brass"]), "motion_overlay")
    _mark(_torus("GoldenCanopyInnerWine", rotor, (0.0, 0.0, inner_z - 0.010), canopy_inner, 0.045, mats["wine"]), "motion_overlay")

    # Ten wide bays and hanging ribbon garlands create a different side rhythm from the old recipe.
    support_count = int(geo["supportCount"])
    support_r = float(geo["supportRadius"])
    garland_z = float(geo["garlandDropZ"])
    for i in range(support_count):
        a = 2.0 * math.pi * i / support_count
        x, y = support_r * math.cos(a), support_r * math.sin(a)
        pole = _cylinder(
            f"GoldenSupport_{i:02d}", rotor,
            (x, y, (platform_z + outer_z) * 0.5),
            0.045, outer_z - platform_z, mats["brass"], vertices=14
        )
        _mark(pole, "motion_overlay")
        _mark(_sphere(f"GoldenSupportCap_{i:02d}", rotor, (x, y, outer_z - 0.06), (0.085, 0.085, 0.085), mats["jade"] if i % 2 else mats["crimson"], 12, 7), "motion_overlay")

        a_next = 2.0 * math.pi * (i + 1) / support_count
        mid_a = (a + a_next) * 0.5
        next_x, next_y = support_r * math.cos(a_next), support_r * math.sin(a_next)
        mid_x, mid_y = (support_r + 0.05) * math.cos(mid_a), (support_r + 0.05) * math.sin(mid_a)
        _mark(_cylinder_between(f"GoldenGarlandA_{i:02d}", rotor, (x, y, outer_z - 0.14), (mid_x, mid_y, garland_z), 0.027, mats["brass"], 10), "motion_overlay")
        _mark(_cylinder_between(f"GoldenGarlandB_{i:02d}", rotor, (mid_x, mid_y, garland_z), (next_x, next_y, outer_z - 0.14), 0.027, mats["brass"], 10), "motion_overlay")
        _mark(_sphere(f"GoldenGarlandDrop_{i:02d}", rotor, (mid_x, mid_y, garland_z - 0.04), (0.075, 0.075, 0.10), mats["crimson"] if i % 2 == 0 else mats["jade"], 12, 7), "motion_overlay")

    # Warm edge bulbs, sparse enough to remain readable after sprite downsample.
    bulb_count = int(geo.get("bulbCount", 30))
    for i in range(bulb_count):
        a = 2.0 * math.pi * (i + 0.5) / bulb_count
        r = canopy_r - 0.12
        _mark(_sphere(f"GoldenCanopyBulb_{i:02d}", rotor, (r * math.cos(a), r * math.sin(a), outer_z - 0.19), (0.040, 0.040, 0.040), mats["bulb"], 10, 6), "motion_overlay")

    # Hexagonal lantern crown: unmistakably different from the old horse/jewel topper.
    _mark(_cylinder("GoldenLanternBase", rotor, (0.0, 0.0, inner_z + 0.11), 0.66, 0.18, mats["wine"], vertices=12), "motion_overlay")
    lantern_z = float(geo["lanternBodyZ"])
    lantern_r = float(geo["lanternRadius"])
    _mark(_cylinder("GoldenLanternBody", rotor, (0.0, 0.0, lantern_z), lantern_r, 0.40, mats["jade"], vertices=6), "motion_overlay")
    for i in range(6):
        a = 2.0 * math.pi * i / 6.0
        r = lantern_r + 0.025
        plate = _cube(f"GoldenLanternWindow_{i:02d}", rotor, (r * math.cos(a), r * math.sin(a), lantern_z), (0.025, 0.115, 0.12), mats["ivory"], bevel=0.014)
        plate.rotation_euler[2] = a
        _mark(plate, "motion_overlay")
    roof_z = float(geo["lanternRoofZ"])
    _mark(_cone("GoldenLanternRoof", rotor, (0.0, 0.0, roof_z), 0.58, 0.10, 0.34, mats["sunflower"], vertices=6), "motion_overlay")
    _mark(_cylinder("GoldenLanternFinialStem", rotor, (0.0, 0.0, roof_z + 0.27), 0.035, 0.26, mats["brass"], vertices=12), "motion_overlay")
    _mark(_sphere("GoldenLanternFinial", rotor, (0.0, 0.0, roof_z + 0.43), (0.10, 0.10, 0.13), mats["brass"], 14, 8), "motion_overlay")

    animation = recipe["animation"]
    frame_start = int(animation.get("frameStart", 1))
    loop_frame = int(animation.get("loopClosureFrame", 49))
    horse_count = int(geo["horseCount"])
    inner_ring = float(geo["horseInnerRadius"])
    outer_ring = float(geo["horseOuterRadius"])
    for i in range(horse_count):
        ring = outer_ring if i % 2 == 0 else inner_ring
        angle = 2.0 * math.pi * i / horse_count
        _build_mount(i, rotor, angle, ring, mats, geo, frame_start, loop_frame)

    rotor.rotation_euler[2] = 0.0
    rotor.keyframe_insert(data_path="rotation_euler", index=2, frame=frame_start)
    rotor.rotation_euler[2] = 2.0 * math.pi
    rotor.keyframe_insert(data_path="rotation_euler", index=2, frame=loop_frame)
    if rotor.animation_data and rotor.animation_data.action:
        for curve in rotor.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
    rotor.rotation_euler[2] = 0.0

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material(
        "ShadowReceiver",
        receiver["materialColor"],
        float(receiver.get("roughness", 1.0)),
    )
    ground = bs.add_box(
        "ShadowReceiverPlane",
        receiver["location"],
        receiver["dimensions"],
        receiver_mat,
        0.0,
    )

    authored = [obj for obj in scene.objects if obj.type == "MESH" and obj != ground]
    root["runtimeLayerContract"] = "CH_ATTRACTION_MOTION_OVERLAY_V1"
    root["motionActivationTrigger"] = "passenger_boarded"
    root["motionMinimumPassengers"] = 1

    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.14)
    bs.set_direction(root, bs.DIRECTIONS[0])
    scene.frame_set(frame_start)
    bpy.context.view_layer.update()
    return scene, root, rotor, ground, authored


def main():
    args = parse_args()
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    if recipe.get("contract") != "CITY_HORIZON_CAROUSEL_ORIGINAL_V1":
        raise RuntimeError("Golden Ribbon requires CITY_HORIZON_CAROUSEL_ORIGINAL_V1")
    if recipe.get("identity") != "golden_ribbon":
        raise RuntimeError("Golden Ribbon builder requires identity=golden_ribbon")

    studio = bs.load_json(args.studio_preset)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    profile = scene_gate.load_profile(args.preflight_profile)
    scene, root, rotor, ground, authored = build_scene(recipe, studio, out)

    preflight_path = out / "preflight_report.json"
    preflight = scene_gate.run_preflight(
        scene=scene,
        authored=authored,
        footprint=recipe["footprint"],
        profile=profile,
        asset_id=recipe["assetId"],
        report_path=preflight_path,
    )
    scene_gate.require_pass(preflight)

    if args.stage == "preflight":
        _save_blend(args.save_blend)
        print(f"[CH_GATE] Golden Ribbon fresh-build preflight PASS: {preflight_path}")
        return

    bs.set_direction(root, bs.DIRECTIONS[0])
    scene.frame_set(int(recipe["animation"].get("frameStart", 1)))
    bpy.context.view_layer.update()
    proxy = scene_gate.render_proxy(
        scene=scene,
        authored=authored,
        output_path=out / "proxy_south.png",
        profile=profile,
        asset_id=recipe["assetId"],
        direction="south",
    )
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    _save_blend(args.save_blend)
    print(f"[CH_GATE] Golden Ribbon standalone proxy SOUTH ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
