#!/usr/bin/env python3
"""Build an original City Horizon pink flowering tree from a visual archetype."""
from __future__ import annotations

import argparse
import json
import math
import random
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


def make_materials(recipe):
    return {
        key: bs.make_material(
            spec.get("name", key), spec["rgba"], float(spec.get("roughness", 0.8)), float(spec.get("metallic", 0.0))
        )
        for key, spec in recipe["materials"].items()
    }


def tag_parent(obj, root, role, authored, ground=False):
    obj.parent = root
    scene_gate.tag(obj, role, ground_contact=ground)
    authored.append(obj)
    return obj


def cylinder_between(name, a, b, r0, r1, material, root, authored, role, vertices=18):
    a = Vector(a)
    b = Vector(b)
    delta = b - a
    length = delta.length
    mid = (a + b) * 0.5
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r0, radius2=r1, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)
    return tag_parent(obj, root, role, authored, ground=(a.z <= 0.02))


def blob(name, location, scale, material, root, authored, role, subdivisions=3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return tag_parent(obj, root, role, authored)


def flower_spray(name, center, base_scale, mats, rng, root, authored, subdivisions=2, petals=3):
    # Overlapping rounded petals remove the obvious isolated icosphere / low-poly look.
    angle0 = rng.uniform(0.0, math.tau)
    for j in range(petals):
        a = angle0 + j * math.tau / petals + rng.uniform(-0.22, 0.22)
        radius = base_scale * rng.uniform(0.25, 0.55)
        p = center + Vector((
            math.cos(a) * radius,
            math.sin(a) * radius * 0.78,
            rng.uniform(-0.10, 0.16) * base_scale,
        ))
        s = base_scale * rng.uniform(0.72, 1.00)
        blob(
            f"{name}_Petal_{j}", p,
            (s * rng.uniform(0.92, 1.18), s * rng.uniform(0.78, 1.04), s * rng.uniform(0.62, 0.88)),
            mats[j % len(mats)], root, authored, "tree.flower", subdivisions=subdivisions,
        )


def build_tree(root, recipe, mats):
    g = recipe["geometry"]
    rng = random.Random(int(g["seed"]))
    authored = []

    h = float(g["height"])
    trunk_h = float(g["trunkHeight"])
    crown_z = float(g["crownCenterZ"])
    crown_w = float(g["crownWidth"])
    crown_d = float(g["crownDepth"])
    crown_h = float(g["crownHeight"])
    trunk_r = float(g["trunkBaseRadius"])
    branch_segments = int(g.get("branchRadialSegments", 18))
    foliage_subdivisions = int(g.get("foliageSubdivisions", 3))
    flower_subdivisions = int(g.get("flowerSubdivisions", 2))
    petals_per_cluster = int(g.get("petalsPerFlowerCluster", 3))

    # Smooth continuous trunk with a gentle organic lean.
    trunk_mid = Vector((0.05, 0.015, trunk_h * 0.53))
    trunk_top = Vector((0.18, 0.06, trunk_h))
    cylinder_between("MainTrunkLower", (0, 0, 0.0), trunk_mid, trunk_r, trunk_r * 0.72, mats["trunkWarm"], root, authored, "tree.trunk", branch_segments)
    cylinder_between("MainTrunkUpper", trunk_mid, trunk_top, trunk_r * 0.72, trunk_r * 0.43, mats["trunkWarm"], root, authored, "tree.trunk", branch_segments)

    # Narrow shadow strip gives the bark depth without creating a segmented trunk.
    cylinder_between(
        "MainTrunkShadow", (-0.055, 0.06, 0.16), (0.115, 0.105, trunk_h * 0.97),
        trunk_r * 0.22, trunk_r * 0.09, mats["trunkDark"], root, authored, "tree.trunk_detail", branch_segments,
    )

    primary_tips = []
    primary_count = int(g["primaryBranchCount"])
    for i in range(primary_count):
        angle = math.radians(-165 + i * (330 / max(primary_count - 1, 1)))
        radial = 1.45 + 0.46 * math.sin(i * 1.55 + 0.3)
        start = trunk_top + Vector((0.018 * i, 0.0, -0.07 * (i % 2)))
        bend = start + Vector((math.cos(angle) * radial * 0.42, math.sin(angle) * radial * 0.30, 0.46 + 0.13 * math.sin(i)))
        tip = Vector((math.cos(angle) * radial, math.sin(angle) * radial * 0.72, crown_z - 0.35 + 0.35 * math.sin(i * 1.18)))
        cylinder_between(f"PrimaryBranchA_{i:02d}", start, bend, trunk_r * 0.27, trunk_r * 0.17, mats["trunkWarm"], root, authored, "tree.branch", branch_segments)
        cylinder_between(f"PrimaryBranchB_{i:02d}", bend, tip, trunk_r * 0.17, trunk_r * 0.07, mats["trunkWarm"], root, authored, "tree.branch", branch_segments)
        primary_tips.append(tip)

    sec_count = int(g["secondaryBranchCount"])
    for i in range(sec_count):
        base = primary_tips[i % len(primary_tips)]
        phase = (i / max(sec_count, 1)) * math.tau + rng.uniform(-0.20, 0.20)
        reach = rng.uniform(0.85, 1.95)
        mid = base + Vector((math.cos(phase) * reach * 0.48, math.sin(phase) * reach * 0.35, rng.uniform(0.28, 0.62)))
        tip = base + Vector((math.cos(phase) * reach, math.sin(phase) * reach * 0.72, rng.uniform(0.45, 1.25)))
        tip.x = max(-crown_w * 0.48, min(crown_w * 0.48, tip.x))
        tip.y = max(-crown_d * 0.46, min(crown_d * 0.46, tip.y))
        tip.z = max(crown_z - crown_h * 0.28, min(h - 0.25, tip.z))
        cylinder_between(f"SecondaryBranchA_{i:02d}", base, mid, trunk_r * 0.09, trunk_r * 0.055, mats["trunkDark"], root, authored, "tree.branch_fine", 14)
        cylinder_between(f"SecondaryBranchB_{i:02d}", mid, tip, trunk_r * 0.055, trunk_r * 0.022, mats["trunkDark"], root, authored, "tree.branch_fine", 12)

    # Rounded foliage foundation: more clusters, higher sphere subdivision, and overlapping lobes.
    foliage_count = int(g["foliageClusterCount"])
    foliage_centers = []
    for i in range(foliage_count):
        theta = rng.random() * math.tau
        rr = math.sqrt(rng.random())
        x = math.cos(theta) * crown_w * 0.44 * rr
        y = math.sin(theta) * crown_d * 0.42 * rr
        dome = 1.0 - min(1.0, (x / (crown_w * 0.52)) ** 2 + (y / (crown_d * 0.52)) ** 2)
        z = crown_z + crown_h * (0.10 + 0.34 * dome) + rng.uniform(-0.40, 0.34)
        if x < -1.4:
            z -= 0.26
        if x > 2.0:
            z += 0.12
        sx = rng.uniform(0.58, 0.98)
        sy = rng.uniform(0.48, 0.82)
        sz = rng.uniform(0.42, 0.72)
        mat = mats["leafDark"] if i % 4 else mats["leafLight"]
        blob(f"Foliage_{i:03d}", (x, y, z), (sx, sy, sz), mat, root, authored, "tree.foliage", subdivisions=foliage_subdivisions)
        foliage_centers.append(Vector((x, y, z)))

    # Blossom sprays are layered groups instead of isolated low-poly balls.
    flower_mats = (mats["flowerDeep"], mats["flowerMid"], mats["flowerLight"])
    flower_count = int(g["flowerClusterCount"])
    for i in range(flower_count):
        c = foliage_centers[rng.randrange(len(foliage_centers))]
        offset = Vector((rng.uniform(-0.56, 0.56), rng.uniform(-0.46, 0.46), rng.uniform(-0.16, 0.58)))
        p = c + offset
        scale = rng.uniform(0.15, 0.27)
        # Bias brighter flowers toward the top/front for a softer natural read.
        ordered_mats = flower_mats if (i % 4) else (mats["flowerLight"], mats["flowerMid"], mats["flowerDeep"])
        flower_spray(
            f"Blossom_{i:03d}", p, scale, ordered_mats, rng, root, authored,
            subdivisions=flower_subdivisions, petals=petals_per_cluster,
        )

    # Sparse warm buds/highlights remain small and smooth.
    for i in range(int(g["flowerAccentCount"])):
        c = foliage_centers[(i * 7 + 3) % len(foliage_centers)]
        p = c + Vector((rng.uniform(-0.34, 0.34), rng.uniform(-0.26, 0.26), rng.uniform(0.20, 0.62)))
        s = rng.uniform(0.075, 0.12)
        blob(f"WarmBud_{i:02d}", p, (s, s * 0.82, s * 1.22), mats["flowerWarm"], root, authored, "tree.flower_accent", subdivisions=2)

    return authored


def save_blend(path):
    if path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target))


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    if recipe.get("contract") != "CH_VEGETATION_FLOWERING_TREE_V1":
        raise RuntimeError("Expected CH_VEGETATION_FLOWERING_TREE_V1 recipe")

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bs.clear_scene()
    scene = bs.configure_scene(studio, (512, 512), str(out))
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    mats = make_materials(recipe)
    root = fw.empty("AssetRoot")
    root["assetId"] = recipe["assetId"]
    root["assetType"] = recipe["assetType"]
    root["cameraContract"] = "CH_CAMERA_V1"
    root["studioPreset"] = "CH_TYCOON_STUDIO_V1"
    root["runtimeRepresentation"] = "2D_RGBA_pre_rendered_sprite"
    root["proceduralContract"] = recipe["contract"]
    root["qualityGateContract"] = "CH_SCENE_PREFLIGHT_V1"
    root["designStage"] = "reference_reinterpretation_pass_02_smooth"
    root["groundIncludedInAsset"] = False

    authored = build_tree(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material("ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0)))
    bs.add_box("ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0)

    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.20)
    cdg.ensure_positive_camera_depth(scene, authored, root=root, minimum_depth=2.0)
    bs.set_direction(root, bs.DIRECTIONS[0])
    bpy.context.view_layer.update()

    preflight_path = out / "preflight_report.json"
    preflight = scene_gate.run_preflight(
        scene=scene, authored=authored, footprint=recipe["footprint"], profile=profile,
        asset_id=recipe["assetId"], report_path=preflight_path,
    )
    scene_gate.require_pass(preflight)

    if args.stage == "preflight":
        save_blend(args.save_blend)
        print(f"[CH_GATE] flowering tree preflight PASS: {preflight_path}")
        return

    proxy = scene_gate.render_proxy(
        scene=scene, authored=authored, output_path=out / "proxy_south.png",
        profile=profile, asset_id=recipe["assetId"], direction="south",
    )
    proxy["referenceReinterpretation"] = True
    proxy["designPass"] = 2
    proxy["flowerClusterCount"] = int(recipe["geometry"]["flowerClusterCount"])
    proxy["petalsPerFlowerCluster"] = int(recipe["geometry"].get("petalsPerFlowerCluster", 3))
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] flowering tree SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
