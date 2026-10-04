#!/usr/bin/env python3
"""Build the City Horizon pink flowering tree with defined broadleaf foliage.

The crown deliberately ports the established A7 Forge 2D broadleaf-V5 art
language: branch-guided depth groups made from explicit readable leaves.  In
this Blender adaptation the original green palette is replaced by rose/purple
leaf materials; spherical foliage/blossom blobs are not used.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CH_BLENDER = REPO_ROOT / "tools" / "ch_blender"
for path in (HERE, CH_BLENDER):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

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
            spec.get("name", key), spec["rgba"],
            float(spec.get("roughness", 0.8)), float(spec.get("metallic", 0.0)),
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
    mid = (a + b) * 0.5
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=r0, radius2=r1,
        depth=delta.length, location=mid,
    )
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


def make_leaf_mesh(name, material, segments=16, thickness=0.018):
    """Create one smooth almond leaf mesh, unit length on local X.

    A rounded sin() outline and a slightly raised midrib keep the silhouette
    leaf-like after downsampling.  Several material-specific meshes are shared
    by hundreds of lightweight linked objects.
    """
    segments = max(12, int(segments))
    half = segments // 2
    outline = []
    # Tip -> upper edge -> stem -> lower edge -> tip.
    for i in range(half + 1):
        t = i / half
        x = 0.5 - t
        y = math.sin(math.pi * t) * 0.5
        outline.append((x, y, 0.0))
    for i in range(1, half):
        t = i / half
        x = -0.5 + t
        y = -math.sin(math.pi * t) * 0.5
        outline.append((x, y, 0.0))

    n = len(outline)
    verts = []
    # Convex top/bottom rim plus central midrib gives a soft surface.
    for x, y, _ in outline:
        bow = (1.0 - min(1.0, abs(x) * 2.0)) * thickness * 0.35
        verts.append((x, y, bow))
    for x, y, _ in outline:
        bow = -(1.0 - min(1.0, abs(x) * 2.0)) * thickness * 0.35
        verts.append((x, y, bow))
    top_center = len(verts)
    verts.append((0.0, 0.0, thickness))
    bottom_center = len(verts)
    verts.append((0.0, 0.0, -thickness))

    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((top_center, i, j))
        faces.append((bottom_center, n + j, n + i))
        faces.append((i, n + i, n + j, j))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    mesh.update()
    for poly in mesh.polygons:
        poly.use_smooth = True
    return mesh


def add_leaf(name, mesh, location, length, width_ratio, rotation, root, authored):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.scale = (length, length * width_ratio, 1.0)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = rotation
    return tag_parent(obj, root, "tree.defined_leaf", authored)


def crown_groups(crown_z, crown_w, crown_d, crown_h, primary_tips, secondary_tips, rng, limit):
    """3D counterpart of broadleaf V5 rear / branch / front depth groups."""
    groups = []
    rear = (
        (-.46, -.10, -.10), (-.19, -.39, .04), (.13, -.43, .07), (.43, -.14, -.04),
        (-.31, .19, -.12), (.03, .17, .02), (.36, .18, -.08), (-.02, .40, -.16),
    )
    for ox, oy, oz in rear:
        groups.append((0, Vector((ox*crown_w*.82, oy*crown_d*.82, crown_z + oz*crown_h))))

    for i, tip in enumerate(secondary_tips):
        if len(groups) >= 24:
            break
        p = Vector(tip)
        p += Vector((rng.uniform(-.18, .18), rng.uniform(-.14, .14), rng.uniform(-.08, .28)))
        groups.append((1, p))

    front = (
        (-.39, -.19, .08), (-.13, -.28, .18), (.15, -.25, .17), (.39, -.14, .07),
        (-.30, .07, .12), (-.02, .04, .25), (.27, .08, .14), (-.19, .28, .08),
        (.11, .28, .16), (.36, .24, .05), (-.18, -.52, .21), (.05, -.56, .28),
        (.27, -.47, .20), (.01, .47, -.04),
    )
    for ox, oy, oz in front:
        groups.append((2, Vector((ox*crown_w*.88, oy*crown_d*.86, crown_z + oz*crown_h))))

    return groups[:limit]


def scatter_defined_leaves(groups, recipe, mats, rng, root, authored):
    g = recipe["geometry"]
    meshes = {
        "back": make_leaf_mesh("PinkLeafPlumMesh", mats["leafBack"], g["leafOutlineSegments"], g["leafThickness"]),
        "mid": make_leaf_mesh("PinkLeafBerryMesh", mats["leafMid"], g["leafOutlineSegments"], g["leafThickness"]),
        "front": make_leaf_mesh("PinkLeafRoseMesh", mats["leafFront"], g["leafOutlineSegments"], g["leafThickness"]),
        "highlight": make_leaf_mesh("PinkLeafLilacMesh", mats["leafHighlight"], g["leafOutlineSegments"], g["leafThickness"]),
        "warm": make_leaf_mesh("PinkLeafWarmMesh", mats["leafWarm"], g["leafOutlineSegments"], g["leafThickness"]),
    }
    lmin = float(g["leafLengthMin"])
    lmax = float(g["leafLengthMax"])
    wr_min = float(g["leafWidthRatioMin"])
    wr_max = float(g["leafWidthRatioMax"])

    leaf_index = 0
    for gi, (depth, center) in enumerate(groups):
        if depth == 0:
            count = int(g["leavesPerRearGroup"])
            spread = Vector((0.82, 0.60, 0.50))
        elif depth == 1:
            count = int(g["leavesPerMidGroup"])
            spread = Vector((0.90, 0.67, 0.57))
        else:
            count = int(g["leavesPerFrontGroup"])
            spread = Vector((0.94, 0.70, 0.61))

        for li in range(count):
            # Ellipsoidal distribution keeps each group connected while leaf
            # silhouettes remain discrete, matching the V5 defined-leaf intent.
            for _ in range(12):
                dx = rng.uniform(-1.0, 1.0)
                dy = rng.uniform(-1.0, 1.0)
                dz = rng.uniform(-1.0, 1.0)
                if dx*dx + dy*dy + dz*dz <= 1.0:
                    break
            p = center + Vector((dx*spread.x, dy*spread.y, dz*spread.z))

            if depth == 0:
                key = "back" if rng.random() < .72 else "mid"
            elif depth == 1:
                roll = rng.random()
                key = "mid" if roll < .60 else ("front" if roll < .92 else "highlight")
            else:
                roll = rng.random()
                key = "front" if roll < .58 else ("highlight" if roll < .90 else "mid")
                if rng.random() < .025:
                    key = "warm"

            length = rng.uniform(lmin, lmax) * (0.94 if depth == 0 else 1.0)
            ratio = rng.uniform(wr_min, wr_max)
            # Leaves tend to radiate away from the crown center, with enough
            # random tilt to stop the canopy from reading as stacked cards.
            yaw = math.atan2(p.y, p.x) + rng.uniform(-0.72, 0.72)
            pitch = rng.uniform(-0.52, 0.52)
            roll = rng.uniform(-0.62, 0.62)
            add_leaf(
                f"DefinedLeaf_{leaf_index:04d}", meshes[key], p, length, ratio,
                Euler((roll, pitch, yaw)), root, authored,
            )
            leaf_index += 1
    return leaf_index


def build_tree(root, recipe, mats):
    g = recipe["geometry"]
    rng = random.Random(int(g["seed"]))
    authored = []
    trunk_h = float(g["trunkHeight"])
    crown_z = float(g["crownCenterZ"])
    crown_w = float(g["crownWidth"])
    crown_d = float(g["crownDepth"])
    crown_h = float(g["crownHeight"])
    trunk_r = float(g["trunkBaseRadius"])
    radial_segments = int(g.get("branchRadialSegments", 18))

    trunk_mid = Vector((0.05, 0.015, trunk_h * 0.53))
    trunk_top = Vector((0.18, 0.06, trunk_h))
    cylinder_between("MainTrunkLower", (0, 0, 0), trunk_mid, trunk_r, trunk_r*.72, mats["trunkWarm"], root, authored, "tree.trunk", radial_segments)
    cylinder_between("MainTrunkUpper", trunk_mid, trunk_top, trunk_r*.72, trunk_r*.43, mats["trunkWarm"], root, authored, "tree.trunk", radial_segments)
    cylinder_between("MainTrunkShadow", (-.055,.06,.16), (.115,.105,trunk_h*.97), trunk_r*.22, trunk_r*.09, mats["trunkDark"], root, authored, "tree.trunk_detail", radial_segments)

    primary_tips = []
    for i in range(int(g["primaryBranchCount"])):
        a = math.radians(-165 + i * (330 / max(int(g["primaryBranchCount"])-1, 1)))
        reach = 1.48 + .44*math.sin(i*1.55+.3)
        start = trunk_top + Vector((.018*i, 0, -.07*(i%2)))
        bend = start + Vector((math.cos(a)*reach*.42, math.sin(a)*reach*.30, .46+.13*math.sin(i)))
        tip = Vector((math.cos(a)*reach, math.sin(a)*reach*.72, crown_z-.40+.34*math.sin(i*1.18)))
        cylinder_between(f"PrimaryBranchA_{i:02d}", start, bend, trunk_r*.27, trunk_r*.17, mats["trunkWarm"], root, authored, "tree.branch", radial_segments)
        cylinder_between(f"PrimaryBranchB_{i:02d}", bend, tip, trunk_r*.17, trunk_r*.07, mats["trunkWarm"], root, authored, "tree.branch", radial_segments)
        primary_tips.append(tip)

    secondary_tips = []
    for i in range(int(g["secondaryBranchCount"])):
        base = primary_tips[i % len(primary_tips)]
        phase = (i / int(g["secondaryBranchCount"])) * math.tau + rng.uniform(-.20,.20)
        reach = rng.uniform(.85,1.95)
        mid = base + Vector((math.cos(phase)*reach*.48, math.sin(phase)*reach*.35, rng.uniform(.28,.62)))
        tip = base + Vector((math.cos(phase)*reach, math.sin(phase)*reach*.72, rng.uniform(.45,1.25)))
        tip.x = max(-crown_w*.48, min(crown_w*.48, tip.x))
        tip.y = max(-crown_d*.46, min(crown_d*.46, tip.y))
        tip.z = max(crown_z-crown_h*.28, min(float(g["height"])-.25, tip.z))
        cylinder_between(f"SecondaryBranchA_{i:02d}", base, mid, trunk_r*.09, trunk_r*.055, mats["trunkDark"], root, authored, "tree.branch_fine", 14)
        cylinder_between(f"SecondaryBranchB_{i:02d}", mid, tip, trunk_r*.055, trunk_r*.022, mats["trunkDark"], root, authored, "tree.branch_fine", 12)
        secondary_tips.append(tip)

    groups = crown_groups(crown_z, crown_w, crown_d, crown_h, primary_tips, secondary_tips, rng, int(g["leafGroupCount"]))
    leaf_count = scatter_defined_leaves(groups, recipe, mats, rng, root, authored)
    root["definedLeafCount"] = leaf_count
    root["leafRecipeSource"] = recipe["leafRecipeSource"]["path"]
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
    root["designStage"] = "defined_leaf_recipe_pass_03"
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
        print(f"[CH_GATE] flowering tree defined-leaf preflight PASS: {preflight_path}")
        return

    proxy = scene_gate.render_proxy(
        scene=scene, authored=authored, output_path=out / "proxy_south.png",
        profile=profile, asset_id=recipe["assetId"], direction="south",
    )
    proxy["referenceReinterpretation"] = True
    proxy["designPass"] = 3
    proxy["leafRecipeSource"] = recipe["leafRecipeSource"]
    proxy["definedLeafCount"] = int(root.get("definedLeafCount", 0))
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] flowering tree defined-leaf SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
