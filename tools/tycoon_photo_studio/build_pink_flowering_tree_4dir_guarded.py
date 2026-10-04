#!/usr/bin/env python3
"""Render the approved City Horizon pink flowering tree in all four canonical directions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

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
import build_pink_flowering_tree_guarded as tree  # noqa: E402


def main():
    args = tree.parse_args()
    recipe = tree.load_json(args.recipe)
    if recipe.get("contract") != "CH_VEGETATION_FLOWERING_TREE_V1":
        raise RuntimeError("Expected CH_VEGETATION_FLOWERING_TREE_V1 recipe")

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bs.clear_scene()
    source_res = tuple(map(int, studio["render"]["sourceResolution"]))
    scene = bs.configure_scene(studio, source_res, str(out))
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    mats = tree.make_materials(recipe)
    root = fw.empty("AssetRoot")
    root["assetId"] = recipe["assetId"]
    root["assetType"] = recipe["assetType"]
    root["cameraContract"] = "CH_CAMERA_V1"
    root["studioPreset"] = "CH_TYCOON_STUDIO_V1"
    root["groundIncludedInAsset"] = False
    root["runtimeRepresentation"] = "2D_RGBA_pre_rendered_sprite"
    root["proceduralContract"] = recipe["contract"]
    root["qualityGateContract"] = "CH_SCENE_PREFLIGHT_V1"
    root["designStage"] = "four_direction_proxy_v1"

    authored = tree.build_tree(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material(
        "ShadowReceiver",
        receiver["materialColor"],
        float(receiver.get("roughness", 1.0)),
    )
    bs.add_box(
        "ShadowReceiverPlane",
        receiver["location"],
        receiver["dimensions"],
        receiver_mat,
        0.0,
    )

    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.20)
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
        tree.save_blend(args.save_blend)
        print(f"[CH_GATE] pink flowering tree four-direction preflight PASS: {preflight_path}")
        return

    reports = {}
    for direction in bs.DIRECTIONS:
        direction_id = direction["id"]
        bs.set_direction(root, direction)
        bpy.context.view_layer.update()
        report = scene_gate.render_proxy(
            scene=scene,
            authored=authored,
            output_path=out / f"proxy_{direction_id}.png",
            profile=profile,
            asset_id=recipe["assetId"],
            direction=direction_id,
        )
        reports[direction_id] = report
        print(f"[CH_GATE] pink tree {direction_id.upper()} proxy ready: {report['sha256']}")

    bs.set_direction(root, bs.DIRECTIONS[0])
    bpy.context.view_layer.update()

    # Generic guarded jobs expect the canonical SOUTH report at proxy_report.json.
    (out / "proxy_report.json").write_text(
        json.dumps(reports["south"], indent=2), encoding="utf-8"
    )
    (out / "proxy_set_report.json").write_text(
        json.dumps({
            "contract": "CH_PROXY_RENDER_SET_V1",
            "status": "ok",
            "assetId": recipe["assetId"],
            "directions": [direction["id"] for direction in bs.DIRECTIONS],
            "views": reports,
        }, indent=2),
        encoding="utf-8",
    )
    tree.save_blend(args.save_blend)
    print("[CH_GATE] pink flowering tree four-direction proxy set ready")


if __name__ == "__main__":
    main()
