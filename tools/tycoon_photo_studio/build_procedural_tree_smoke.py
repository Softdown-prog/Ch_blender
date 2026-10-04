"""Lightweight first-run smoke render for the Windows CH Blender runner.

Builds the existing deterministic broadleaf procedural 3D tree geometry, but renders
only the canonical SOUTH color pass at low Cycles resolution/samples. This file is
for runner/backend validation and visual inspection, not production promotion.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_scene as studio_base
import build_classic_tree as classic_tree


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--asset-config",
        default="tools/tycoon_photo_studio/assets/park_tree_broadleaf_02.fractal.json",
    )
    parser.add_argument(
        "--studio-preset",
        default="tools/tycoon_photo_studio/studio_presets/ch_tycoon_studio_v1.json",
    )
    parser.add_argument("--resolution", type=int, default=320)
    parser.add_argument("--samples", type=int, default=4)
    return parser.parse_args(argv)


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    asset = load_json(args.asset_config)
    studio = load_json(args.studio_preset)
    if asset.get("studioPreset") != studio.get("id"):
        raise RuntimeError("Tree source and studio preset do not match")

    resolution = max(128, min(512, int(args.resolution)))
    samples = max(1, min(16, int(args.samples)))

    studio_base.clear_scene()
    scene = studio_base.configure_scene(studio, (resolution, resolution), str(output_dir))
    if scene.render.engine != "CYCLES":
        raise RuntimeError(f"Smoke test requires Cycles, got {scene.render.engine}")
    scene.cycles.samples = samples
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = False

    authored, branch_count, leaf_count = classic_tree.build_tree(asset)
    root = studio_base.create_asset_root(authored)
    calibrated_scale = studio_base.calibrate_ortho_scale(scene, authored)

    receiver = studio["shadowReceiver"]
    ground_material = studio_base.make_material(
        "TreeSmokeShadowReceiver",
        receiver["materialColor"],
        float(receiver.get("roughness", 1.0)),
    )
    ground = studio_base.add_box(
        "ShadowReceiverPlane",
        receiver["location"],
        receiver["dimensions"],
        ground_material,
        0.0,
    )

    south = next(direction for direction in studio_base.DIRECTIONS if direction["id"] == "south")
    studio_base.set_direction(root, south)
    image_name = "procedural_tree_broadleaf_02_south_smoke.png"
    image_path = output_dir / image_name
    studio_base.render_color_pass(scene, authored, ground, str(image_path))

    metadata = {
        "contract": "CH_BLENDER_PROCEDURAL_TREE_SMOKE_V1",
        "status": "ok",
        "assetId": asset["assetId"],
        "sourceContract": asset["contract"],
        "cameraContract": studio["camera"]["contract"],
        "direction": "south",
        "blenderVersion": bpy.app.version_string,
        "renderEngine": scene.render.engine,
        "device": "CPU",
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "samples": scene.cycles.samples,
        "denoising": False,
        "branchCount": branch_count,
        "leafCardCount": leaf_count,
        "authoredPartCount": len(authored),
        "orthoScale": scene.camera.data.ortho_scale,
        "orthoScaleCalibrated": calibrated_scale,
        "output": image_name,
        "purpose": "Windows self-hosted Legacy CPU runner connectivity smoke test",
    }
    (output_dir / "smoke_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
