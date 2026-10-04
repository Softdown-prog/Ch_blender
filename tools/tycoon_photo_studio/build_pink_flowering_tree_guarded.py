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


def cylinder_between(name, a, b, r0, r1, material, root, authored, role):
    a = Vector(a); b = Vector(b)
    delta = b - a
    length = delta.length
    mid = (a + b) * 0.5
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r0, radius2=r1, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return tag_parent(obj, root, role, authored, ground=(a.z <= 0.02))


def blob(name, location, scale, material, root, authored, role, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return tag_parent(obj, root, role, authored)


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

    # Slightly leaning main trunk; continuous silhouette rather than stacked segments.
    trunk_top = Vector((0.18, 0.06, trunk_h))
    cylinder_between("MainTrunk", (0, 0, 0.0), trunk_top, trunk_r, trunk_r * 0.48, mats["trunkWarm"], root, authored, "tree.trunk")
    cylinder_between("MainTrunkShadow", (-0.05, 0.055, 0.15), (0.12, 0.10, trunk_h * 0.98), trunk_r * 0.44, trunk_r * 0.22, mats["trunkDark"], root, authored, "tree.trunk_detail")

    # Primary limbs: readable fan shape, biased outward to expose the trunk beneath the crown.
    primary_tips = []
    primary_count = int(g["primaryBranchCount"])
    for i in range(primary_count):
        angle = math.radians(-165 + i * (330 / max(primary_count - 1, 1)))
        radial = 1.65 + 0.35 * math.sin(i * 1.7)
        start = trunk_top + Vector((0.03 * i, 0.0, -0.08 * (i % 2)))
        tip = Vector((math.cos(angle) * radial, math.sin(angle) * radial * 0.72, crown_z - 0.38 + 0.34 * math.sin(i * 1.2)))
        cylinder_between(f"PrimaryBranch_{i:02d}", start, tip, trunk_r * 0.30, trunk_r * 0.10, mats["trunkWarm"], root, authored, "tree.branch")
        primary_tips.append(tip)

    # Secondary branches split toward upper/lateral flower masses.
    sec_count = int(g["secondaryBranchCount"])
    secondary_tips = []
    for i in range(sec_count):
        base = primary_tips[i % len(primary_tips)]
        phase = (i / max(sec_count, 1)) * math.tau
        reach = rng.uniform(1.0, 2.15)
        tip = base + Vector((math.cos(phase) * reach, math.sin(phase) * reach * 0.72, rng.uniform(0.25, 1.35)))
        # Keep branch endpoints inside the intended crown envelope.
        tip.x = max(-crown_w * 0.48, min(crown_w * 0.48, tip.x))
        tip.y = max(-crown_d * 0.46, min(crown_d * 0.46, tip.y))
        tip.z = max(crown_z - crown_h * 0.28, min(h - 0.25, tip.z))
        cylinder_between(f"SecondaryBranch_{i:02d}", base, tip, trunk_r * 0.11, trunk_r * 0.035, mats["trunkDark"], root, authored, "tree.branch_fine")
        secondary_tips.append(tip)

    # Dark green masses sit behind the blossoms to keep crown depth and avoid a flat pink cloud.
    foliage_count = int(g["foliageClusterCount"])
    foliage_centers = []
    for i in range(foliage_count):
        theta = rng.random() * math.tau
        rr = math.sqrt(rng.random())
        x = math.cos(theta) * crown_w * 0.43 * rr
        y = math.sin(theta) * crown_d * 0.42 * rr
        dome = 1.0 - min(1.0, (x / (crown_w * 0.52)) ** 2 + (y / (crown_d * 0.52)) ** 2)
        z = crown_z + crown_h * (0.12 + 0.36 * dome) + rng.uniform(-0.45, 0.38)
        # Create a broad umbrella edge and a slightly lower left lobe.
        if x < -1.4:
            z -= 0.28
        sx = rng.uniform(0.48, 0.88)
        sy = rng.uniform(0.40, 0.72)
        sz = rng.uniform(0.36, 0.68)
        mat = mats["leafDark"] if i % 3 else mats["leafLight"]
        blob(f"Foliage_{i:03d}", (x, y, z), (sx, sy, sz), mat, root, authored, "tree.foliage", subdivisions=2)
        foliage_centers.append(Vector((x, y, z)))

    # Dense blossom clusters layer over the green masses. Three pink values preserve detail at sprite scale.
    flower_mats = (mats["flowerDeep"], mats["flowerMid"], mats["flowerLight"])
    flower_count = int(g["flowerClusterCount"])
    for i in range(flower_count):
        c = foliage_centers[rng.randrange(len(foliage_centers))]
        offset = Vector((rng.uniform(-0.52, 0.52), rng.uniform(-0.44, 0.44), rng.uniform(-0.22, 0.52)))
        p = c + offset
        scale = rng.uniform(0.19, 0.36)
        # Small anisotropic clusters approximate grouped blossoms without photoreal micro-geometry.
        blob(
            f"Blossom_{i:03d}", p,
            (scale * rng.uniform(0.9, 1.35), scale * rng.uniform(0.8, 1.15), scale * rng.uniform(0.75, 1.10)),
            flower_mats[i % 3], root, authored, "tree.flower", subdivisions=1
        )

    # Sparse warm buds/highlights echo the yellow-green flecks in the reference without copying it literally.
    for i in range(int(g["flowerAccentCount"])):
        c = foliage_centers[(i * 7 + 3) % len(foliage_centers)]
        p = c + Vector((rng.uniform(-0.34, 0.34), rng.uniform(-0.26, 0.26), rng.uniform(0.20, 0.62)))
        s = rng.uniform(0.09, 0.15)
        blob(f"WarmBud_{i:02d}", p, (s, s * 0.8, s * 1.25), mats["flowerWarm"], root, authored, "tree.flower_accent", subdivisions=1)

    return authored


def save_blend(path):
    if path:
        target = Path(path).resolve(); target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target))


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    if recipe.get("contract") != "CH_VEGETATION_FLOWERING_TREE_V1":
        raise RuntimeError("Expected CH_VEGETATION_FLOWERING_TREE_V1 recipe")

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)

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
    root["designStage"] = "reference_reinterpretation_pass_01"
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
    proxy["flowerClusterCount"] = int(recipe["geometry"]["flowerClusterCount"])
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] flowering tree SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
