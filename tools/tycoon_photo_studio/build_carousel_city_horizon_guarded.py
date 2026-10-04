#!/usr/bin/env python3
"""Fresh City Horizon carousel authoring pass.

No legacy carousel builder, recipe, geometry, palette or proportions are reused.
The asset stays inside the City Horizon 4x4 gameplay footprint while progressively
moving from blockout to a readable stylized amusement-ride silhouette.
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
import build_ferris_wheel as fw  # noqa: E402
import camera_depth_guard as cdg  # noqa: E402
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


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_blend(path):
    if not path:
        return
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(target))


def make_materials(recipe):
    return {
        key: bs.make_material(
            spec.get("name", key),
            spec["rgba"],
            float(spec.get("roughness", 0.72)),
            float(spec.get("metallic", 0.0)),
        )
        for key, spec in recipe["materials"].items()
    }


def build_sloped_wedge(name, r_inner, r_outer, inner_top_z, outer_top_z, thickness, a0, a1, material, parent):
    verts = []
    for zoff in (-thickness, 0.0):
        for r, a, z in (
            (r_inner, a0, inner_top_z),
            (r_outer, a0, outer_top_z),
            (r_outer, a1, outer_top_z),
            (r_inner, a1, inner_top_z),
        ):
            verts.append((r * math.cos(a), r * math.sin(a), z + zoff))
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    return obj


def sphere_part(name, location, scale, material, parent, rotation_z=0.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=tuple(location))
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(scale)
    obj.rotation_euler[2] = rotation_z
    obj.data.materials.append(material)
    obj.parent = parent
    return obj


def cone_part(name, location, radius, depth, material, parent, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=radius, radius2=0.0, depth=depth, location=tuple(location), rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj.parent = parent
    return obj


def horse_sculpt(root, idx, angle, radius, platform_z, mats, g):
    """Rounded low-poly carousel mount designed to stay readable after sprite downsample."""
    z = platform_z + float(g["horseBodyZ"])
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    tangent = angle + math.pi * 0.5
    forward = Vector((math.cos(tangent), math.sin(tangent), 0.0))
    side = Vector((-math.sin(tangent), math.cos(tangent), 0.0))

    length = float(g["horseBodyLength"])
    width = float(g["horseBodyWidth"])
    height = float(g["horseBodyHeight"])

    body = sphere_part(
        f"HorseBody_{idx:02d}", (x, y, z),
        (length * 0.52, width * 0.62, height * 0.58), mats["horseIvory"], root, tangent,
    )

    chest = Vector((x, y, z + 0.08)) + forward * (length * 0.31)
    sphere_part(
        f"HorseChest_{idx:02d}", chest,
        (width * 0.43, width * 0.40, height * 0.48), mats["horseIvory"], root, tangent,
    )

    neck_center = Vector((x, y, z + 0.28)) + forward * float(g["horseNeckForward"])
    fw.cylinder(
        f"HorseNeck_{idx:02d}", tuple(neck_center),
        width * 0.19, height * 0.95, mats["horseIvory"],
        rotation=(0.0, math.radians(-28.0), tangent), parent=root, vertices=14,
    )

    head_center = neck_center + forward * 0.18 + Vector((0.0, 0.0, height * 0.42))
    sphere_part(
        f"HorseHead_{idx:02d}", head_center,
        (length * 0.19, width * 0.29, height * 0.27), mats["horseIvory"], root, tangent,
    )
    muzzle_center = head_center + forward * (length * 0.18) - Vector((0.0, 0.0, height * 0.04))
    sphere_part(
        f"HorseMuzzle_{idx:02d}", muzzle_center,
        (length * 0.14, width * 0.24, height * 0.16), mats["horseIvory"], root, tangent,
    )

    for ear_i, side_sign in enumerate((-1.0, 1.0)):
        ear = head_center - forward * 0.03 + side * (side_sign * width * 0.14) + Vector((0.0, 0.0, height * 0.29))
        cone_part(
            f"HorseEar_{idx:02d}_{ear_i}", ear,
            width * 0.07, height * 0.26, mats["horseIvory"], root,
            rotation=(0.0, math.radians(-8.0), tangent),
        )

    # Four legs with a mild alternating carousel pose instead of blockout stilts.
    leg_specs = (
        (+0.28, -0.18, +0.08),
        (+0.28, +0.18, -0.05),
        (-0.27, -0.18, -0.04),
        (-0.27, +0.18, +0.07),
    )
    for leg_i, (fwd_scale, side_scale, lift) in enumerate(leg_specs):
        upper = Vector((x, y, z - height * 0.31)) + forward * (length * fwd_scale) + side * (width * side_scale)
        leg_len = height * 0.88
        fw.cylinder(
            f"HorseLeg_{idx:02d}_{leg_i}",
            (upper.x, upper.y, upper.z - leg_len * 0.35 + lift),
            width * 0.075, leg_len, mats["horseIvory"],
            rotation=(math.radians(7.0 if leg_i % 2 == 0 else -7.0), 0.0, tangent),
            parent=root, vertices=10,
        )

    pole_z0 = platform_z + 0.24
    pole_z1 = float(g["canopyUnderZ"]) - 0.10
    fw.cylinder(
        f"HorsePole_{idx:02d}", (x, y, (pole_z0 + pole_z1) * 0.5),
        float(g["horsePoleRadius"]), pole_z1 - pole_z0,
        mats["metalWarm"], parent=root, vertices=14,
    )

    saddle_center = Vector((x, y, z + height * 0.40)) - forward * (length * 0.04)
    saddle = sphere_part(
        f"HorseSaddle_{idx:02d}", saddle_center,
        (length * 0.23, width * 0.42, height * 0.16), mats["accentCoral"], root, tangent,
    )
    return [body, saddle]


def build_carousel(root, recipe, mats):
    g = recipe["geometry"]
    authored = []

    def box(name, location, dimensions, mat, bevel=0.04, role="carousel.structure", contact=False):
        obj = fw.box(name, location, dimensions, mat, bevel, root)
        scene_gate.tag(obj, role, ground_contact=contact)
        authored.append(obj)
        return obj

    def cyl(name, location, radius, depth, mat, role="carousel.structure", contact=False, vertices=48):
        obj = fw.cylinder(name, location, radius, depth, mat, parent=root, vertices=vertices)
        scene_gate.tag(obj, role, ground_contact=contact)
        authored.append(obj)
        return obj

    base_r = float(g["baseRadius"])
    base_h = float(g["baseHeight"])
    cyl("PlinthLower", (0, 0, base_h * 0.18), base_r, base_h * 0.36, mats["baseDeep"], "carousel.base", True, 32)
    cyl("PlinthMiddle", (0, 0, base_h * 0.48), base_r * 0.94, base_h * 0.24, mats["baseWarm"], "carousel.base", True, 32)
    cyl("PlinthDeck", (0, 0, base_h * 0.78), base_r * 0.90, base_h * 0.24, mats["deckWood"], "carousel.deck", True, 48)
    platform_z = base_h

    mast_r = float(g["mastRadius"])
    mast_top = float(g["mastTopZ"])
    cyl("CenterMast", (0, 0, (platform_z + mast_top) * 0.5), mast_r, mast_top - platform_z, mats["metalWarm"], "carousel.mast")

    crown_z = mast_top + float(g["crownHeight"]) * 0.38
    cyl("CrownDrum", (0, 0, crown_z), float(g["crownRadius"]), float(g["crownHeight"]) * 0.34, mats["accentTeal"], "carousel.crown", False, 24)
    bpy.ops.mesh.primitive_cone_add(
        vertices=24, radius1=float(g["crownRadius"]) * 0.90, radius2=0.0,
        depth=float(g["crownHeight"]) * 0.72,
        location=(0, 0, crown_z + float(g["crownHeight"]) * 0.46),
    )
    crown = bpy.context.object
    crown.name = "CrownCap"
    crown.data.materials.append(mats["accentCoral"])
    crown.parent = root
    scene_gate.tag(crown, "carousel.crown", ground_contact=False)
    authored.append(crown)

    canopy_r = float(g["canopyRadius"])
    inner_r = float(g["canopyInnerRadius"])
    outer_top = float(g["canopyTopZ"])
    peak_rise = float(g.get("canopyPeakRise", 0.0))
    inner_top = outer_top + peak_rise
    canopy_thickness = float(g["canopyThickness"])
    panel_count = int(g["canopyPanelCount"])
    for i in range(panel_count):
        a0 = (2.0 * math.pi * i / panel_count) + float(g["canopyPhaseRadians"])
        a1 = (2.0 * math.pi * (i + 1) / panel_count) + float(g["canopyPhaseRadians"])
        mat = mats["canopyCream"] if i % 2 == 0 else mats["canopyTeal"]
        obj = build_sloped_wedge(
            f"CanopyPanel_{i:02d}", inner_r, canopy_r,
            inner_top, outer_top, canopy_thickness, a0, a1, mat, root,
        )
        scene_gate.tag(obj, "carousel.canopy_panel", ground_contact=False)
        authored.append(obj)

    cyl("CanopyInnerDrum", (0, 0, inner_top - canopy_thickness * 0.55), inner_r * 1.05, canopy_thickness * 2.2, mats["canopyWarm"], "carousel.canopy_hub", False, 48)
    ring = fw.torus("CanopyOuterRing", (0, 0, outer_top - canopy_thickness * 0.18), canopy_r - 0.08, 0.085, mats["baseWarm"], parent=root)
    scene_gate.tag(ring, "carousel.canopy_trim", ground_contact=False)
    authored.append(ring)

    valance_count = int(g["valanceCount"])
    valance_r = canopy_r - 0.11
    valance_z = float(g["canopyUnderZ"]) + 0.04
    for i in range(valance_count):
        a = 2.0 * math.pi * i / valance_count
        x, y = valance_r * math.cos(a), valance_r * math.sin(a)
        obj = box(
            f"ValanceTab_{i:02d}", (x, y, valance_z),
            (float(g["valanceWidth"]), float(g["valanceDepth"]), float(g["valanceHeight"])),
            mats["accentCoral"] if i % 2 == 0 else mats["baseWarm"],
            0.07, "carousel.valance",
        )
        obj.rotation_euler[2] = a + math.pi * 0.5
        if i % 2 == 0:
            bulb = sphere_part(
                f"ValanceBulb_{i:02d}",
                (x, y, valance_z - float(g["valanceHeight"]) * 0.34),
                (0.095, 0.095, 0.095), mats["canopyCream"], root,
            )
            scene_gate.tag(bulb, "carousel.ornament", ground_contact=False)
            authored.append(bulb)

    horse_count = int(g["horseCount"])
    inner_horses = int(g["innerHorseCount"])
    outer_horses = horse_count - inner_horses
    idx = 0
    for ring_count, radius, phase in (
        (outer_horses, float(g["horseOuterRadius"]), 0.0),
        (inner_horses, float(g["horseInnerRadius"]), math.pi / max(1, inner_horses)),
    ):
        for j in range(ring_count):
            a = 2.0 * math.pi * j / ring_count + phase
            before = set(bpy.context.scene.objects)
            horse_sculpt(root, idx, a, radius, platform_z, mats, g)
            for obj in bpy.context.scene.objects:
                if obj not in before and obj.type == "MESH":
                    scene_gate.tag(obj, "carousel.horse", ground_contact=False)
                    authored.append(obj)
            idx += 1

    return authored


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    if recipe.get("contract") != "CH_CAROUSEL_FRESH_V1":
        raise RuntimeError("Expected CH_CAROUSEL_FRESH_V1 recipe")

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bs.clear_scene()
    source_res = tuple(map(int, studio["render"]["sourceResolution"]))
    scene = bs.configure_scene(studio, source_res, str(out))
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    mats = make_materials(recipe)
    root = fw.empty("AssetRoot")
    root["assetId"] = recipe["assetId"]
    root["assetType"] = recipe["assetType"]
    root["cameraContract"] = "CH_CAMERA_V1"
    root["studioPreset"] = "CH_TYCOON_STUDIO_V1"
    root["groundIncludedInAsset"] = False
    root["runtimeRepresentation"] = "2D_RGBA_pre_rendered_sprite"
    root["proceduralContract"] = recipe["contract"]
    root["qualityGateContract"] = "CH_SCENE_PREFLIGHT_V1"
    root["designStage"] = "refinement_pass_03_horse_canopy"
    root["legacyCarouselReuse"] = False

    authored = build_carousel(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material("ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0)))
    bs.add_box("ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0)

    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.26)
    cdg.ensure_positive_camera_depth(scene, authored, root=root, minimum_depth=2.0)
    bs.set_direction(root, bs.DIRECTIONS[0])
    bpy.context.view_layer.update()

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
        save_blend(args.save_blend)
        print(f"[CH_GATE] carousel refinement preflight PASS: {preflight_path}")
        return

    proxy = scene_gate.render_proxy(
        scene=scene,
        authored=authored,
        output_path=out / "proxy_south.png",
        profile=profile,
        asset_id=recipe["assetId"],
        direction="south",
    )
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] carousel refinement SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
