#!/usr/bin/env python3
"""Fresh City Horizon carousel blockout.

This builder intentionally does not import or reuse any legacy carousel builder,
recipe, geometry, material palette, or proportions.  The user-supplied image is
used only as a functional reference for the amusement-ride archetype: circular
platform, overhead canopy, center mast and suspended horses.

Stage 0 goal: prove a new silhouette before authoring final horses, ornaments,
color masks, animation, or production sprites.
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


def build_wedge(name, r_inner, r_outer, z0, z1, a0, a1, material, parent):
    verts = []
    for z in (z0, z1):
        for r, a in ((r_inner, a0), (r_outer, a0), (r_outer, a1), (r_inner, a1)):
            verts.append((r * math.cos(a), r * math.sin(a), z))
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


def horse_blockout(root, idx, angle, radius, platform_z, mats, g):
    z = platform_z + float(g["horseBodyZ"])
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    tangent = angle + math.pi * 0.5

    body = fw.box(
        f"HorseBody_{idx:02d}", (x, y, z),
        (float(g["horseBodyLength"]), float(g["horseBodyWidth"]), float(g["horseBodyHeight"])),
        mats["horseIvory"], 0.10, root,
    )
    body.rotation_euler[2] = tangent

    forward = Vector((math.cos(tangent), math.sin(tangent), 0.0))
    neck_center = Vector((x, y, z)) + forward * float(g["horseNeckForward"])
    neck = fw.cylinder(
        f"HorseNeck_{idx:02d}",
        (neck_center.x, neck_center.y, z + 0.22),
        0.11, 0.55, mats["horseIvory"],
        rotation=(0.0, math.radians(-18.0), tangent), parent=root, vertices=16,
    )
    head_center = Vector((neck_center.x, neck_center.y, z + 0.46)) + forward * 0.10
    head = fw.box(
        f"HorseHead_{idx:02d}", (head_center.x, head_center.y, head_center.z),
        (0.34, 0.22, 0.25), mats["horseIvory"], 0.09, root,
    )
    head.rotation_euler[2] = tangent

    for leg_i, offset in enumerate((-0.24, 0.24)):
        p = Vector((x, y, z - 0.10)) + forward * offset
        fw.cylinder(
            f"HorseLeg_{idx:02d}_{leg_i}",
            (p.x, p.y, platform_z + 0.42), 0.055, 0.62,
            mats["horseIvory"], parent=root, vertices=12,
        )

    pole_z0 = platform_z + 0.26
    pole_z1 = float(g["canopyUnderZ"]) - 0.16
    fw.cylinder(
        f"HorsePole_{idx:02d}", (x, y, (pole_z0 + pole_z1) * 0.5),
        float(g["horsePoleRadius"]), pole_z1 - pole_z0,
        mats["metalWarm"], parent=root, vertices=16,
    )

    saddle = fw.box(
        f"HorseSaddle_{idx:02d}",
        (x, y, z + 0.17), (0.36, 0.30, 0.12), mats["accentCoral"], 0.05, root,
    )
    saddle.rotation_euler[2] = tangent
    return [body, neck, head, saddle]


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
    canopy_z = float(g["canopyTopZ"])
    canopy_thickness = float(g["canopyThickness"])
    panel_count = int(g["canopyPanelCount"])
    for i in range(panel_count):
        a0 = (2.0 * math.pi * i / panel_count) + float(g["canopyPhaseRadians"])
        a1 = (2.0 * math.pi * (i + 1) / panel_count) + float(g["canopyPhaseRadians"])
        mat = mats["canopyCream"] if i % 2 == 0 else mats["canopyTeal"]
        obj = build_wedge(f"CanopyPanel_{i:02d}", inner_r, canopy_r, canopy_z - canopy_thickness, canopy_z, a0, a1, mat, root)
        scene_gate.tag(obj, "carousel.canopy_panel", ground_contact=False)
        authored.append(obj)

    cyl("CanopyInnerDrum", (0, 0, canopy_z - canopy_thickness * 0.40), inner_r * 1.04, canopy_thickness * 1.9, mats["canopyWarm"], "carousel.canopy_hub", False, 48)
    fw.torus("CanopyOuterRing", (0, 0, canopy_z - canopy_thickness * 0.16), canopy_r - 0.08, 0.085, mats["baseWarm"], parent=root)
    ring = bpy.context.object
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
            horse_blockout(root, idx, a, radius, platform_z, mats, g)
            for obj in bpy.context.scene.objects:
                if obj not in before and obj.type == "MESH":
                    scene_gate.tag(obj, "carousel.horse_blockout", ground_contact=False)
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
    root["designStage"] = "fresh_original_blockout_v0"
    root["legacyCarouselReuse"] = False

    authored = build_carousel(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material("ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0)))
    bs.add_box("ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0)

    # Large 5x5 attractions need extra framing headroom because the quality gate
    # evaluates every canonical rotation, including the tall crown silhouette.
    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.32)
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
        print(f"[CH_GATE] fresh carousel blockout preflight PASS: {preflight_path}")
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
    print(f"[CH_GATE] fresh carousel SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
