#!/usr/bin/env python3
"""Build City Horizon soda vending machine V2."""
from __future__ import annotations

import argparse
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


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--studio-preset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--save-blend", default=None)
    parser.add_argument("--stage", choices=("preflight", "proxy"), default="preflight")
    parser.add_argument("--preflight-profile", default=None)
    return parser.parse_args(argv)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_materials(recipe):
    return {
        key: bs.make_material(
            spec.get("name", key),
            spec["rgba"],
            float(spec.get("roughness", 0.7)),
            float(spec.get("metallic", 0.0)),
        )
        for key, spec in recipe["materials"].items()
    }


def save_blend(path):
    if path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target))


def build_machine(root, recipe, mats):
    g = recipe["geometry"]
    authored = []

    def box(name, location, dims, mat, bevel=0.04, role="soda.structure", contact=False):
        obj = fw.box(name, location, dims, mat, bevel, root)
        scene_gate.tag(obj, role, ground_contact=contact)
        authored.append(obj)
        return obj

    w = float(g["bodyWidth"])
    d = float(g["bodyDepth"])
    h = float(g["bodyHeight"])
    base_h = float(g["baseHeight"])
    cap_h = float(g["topCapHeight"])
    front_y = -d * 0.5 - 0.012

    # Stronger stepped silhouette than V1, but still compact for a 60 px sprite.
    box("SodaBase", (0, 0, base_h * 0.5), (w * 0.98, d * 0.97, base_h), mats["dark"], 0.035, "soda.base", True)
    box("SodaBody", (0, 0, base_h + h * 0.5), (w, d, h), mats["body"], float(g["cornerBevel"]), "soda.body")
    box("TopCap", (0, 0, base_h + h + cap_h * 0.5), (w * 1.035, d * 1.025, cap_h), mats["cream"], 0.045, "soda.cap")

    # Side inset and lower side rail make the cabinet volume readable in isometric view.
    box("SideInset", (w * 0.505, 0.015, base_h + h * 0.53), (0.040, d * 0.79, h * 0.78), mats["side"], 0.012, "soda.side")
    box("SideRail", (w * 0.515, 0.02, base_h + h * 0.18), (0.032, d * 0.72, 0.08), mats["accent"], 0.012, "soda.trim")

    marquee_h = float(g["marqueeHeight"])
    marquee_z = base_h + h - marquee_h * 0.63
    box("MarqueeFrame", (0, front_y - 0.005, marquee_z), (w * 0.92, 0.070, marquee_h + 0.05), mats["dark"], 0.038, "soda.marquee_frame")
    box("MarqueeFace", (0, front_y - 0.047, marquee_z), (w * 0.85, 0.028, marquee_h), mats["cream"], 0.032, "soda.marquee")

    # Original CH three-stroke emblem; intentionally not a real-world soda logo.
    box("BrandStrokeA", (-0.22, front_y - 0.067, marquee_z + 0.045), (0.25, 0.018, 0.055), mats["accent"], 0.014, "soda.graphic")
    box("BrandStrokeB", (0.00, front_y - 0.068, marquee_z), (0.28, 0.018, 0.055), mats["display"], 0.014, "soda.graphic")
    box("BrandStrokeC", (0.22, front_y - 0.067, marquee_z - 0.045), (0.22, 0.018, 0.055), mats["accent"], 0.014, "soda.graphic")

    display_w = float(g["displayWidth"])
    display_h = float(g["displayHeight"])
    display_z = base_h + h * 0.625
    display_x = -0.075
    box("DisplayFrame", (display_x, front_y - 0.014, display_z), (display_w + 0.10, 0.070, display_h + 0.10), mats["cream"], 0.032, "soda.display_frame")
    box("DisplayInnerFrame", (display_x, front_y - 0.055, display_z), (display_w + 0.035, 0.028, display_h + 0.035), mats["dark"], 0.024, "soda.display_frame")
    box("DisplayGlass", (display_x, front_y - 0.075, display_z), (display_w, 0.020, display_h), mats["display"], 0.020, "soda.display")

    # Three chunky product silhouettes and bright label bands survive downsampling better than detail textures.
    bottle_x = (-0.31, -0.075, 0.16)
    bottle_mats = (mats["green"], mats["cream"], mats["blue"])
    for i, (x, mat) in enumerate(zip(bottle_x, bottle_mats)):
        box(f"BottleBody_{i}", (x, front_y - 0.088, display_z - 0.015), (0.13, 0.018, 0.30), mat, 0.036, "soda.product")
        box(f"BottleNeck_{i}", (x, front_y - 0.089, display_z + 0.155), (0.072, 0.018, 0.075), mat, 0.020, "soda.product")
        box(f"BottleLabel_{i}", (x, front_y - 0.099, display_z - 0.005), (0.105, 0.012, 0.055), mats["accent"] if i != 1 else mats["display"], 0.010, "soda.product")

    control_x = w * 0.35
    control_z = base_h + h * 0.52
    control_w = float(g["controlWidth"])
    control_h = float(g["controlHeight"])
    box("ControlFrame", (control_x, front_y - 0.018, control_z), (control_w + 0.08, 0.075, control_h + 0.08), mats["dark"], 0.027, "soda.controls")
    box("ControlPanel", (control_x, front_y - 0.062, control_z), (control_w, 0.035, control_h), mats["cream"], 0.022, "soda.controls")
    for i in range(3):
        button_z = control_z + 0.145 - i * 0.145
        box(f"SelectButton_{i}", (control_x, front_y - 0.086, button_z), (0.105, 0.020, 0.075), mats["accent"] if i == 0 else mats["metal"], 0.018, "soda.controls")
    box("PaymentSlot", (control_x, front_y - 0.088, control_z - 0.235), (0.115, 0.020, 0.045), mats["dark"], 0.010, "soda.controls")

    vend_w = float(g["vendWidth"])
    vend_h = float(g["vendHeight"])
    vend_z = base_h + h * 0.22
    box("VendBayFrame", (-0.06, front_y - 0.010, vend_z), (vend_w + 0.14, 0.075, vend_h + 0.13), mats["cream"], 0.034, "soda.vend")
    box("VendBayInner", (-0.06, front_y - 0.054, vend_z), (vend_w + 0.045, 0.032, vend_h + 0.045), mats["dark"], 0.027, "soda.vend")
    box("VendBay", (-0.06, front_y - 0.078, vend_z - 0.005), (vend_w, 0.022, vend_h), mats["side"], 0.024, "soda.vend")
    box("VendLip", (-0.06, front_y - 0.091, vend_z - vend_h * 0.36), (vend_w * 0.86, 0.020, 0.055), mats["metal"], 0.012, "soda.vend")

    # Lower trim and kick plate visually anchor the prop on the tile.
    box("LowerAccent", (0, front_y - 0.030, base_h + h * 0.095), (w * 0.78, 0.045, 0.070), mats["accent"], 0.020, "soda.trim")
    box("KickPlate", (0, front_y - 0.020, base_h + 0.035), (w * 0.82, 0.050, 0.070), mats["dark"], 0.018, "soda.trim")

    return authored


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    if recipe.get("contract") != "CH_PROP_SODA_MACHINE_V2":
        raise RuntimeError("Expected CH_PROP_SODA_MACHINE_V2 recipe")

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bs.clear_scene()
    proxy_canvas = int(recipe.get("sprite", {}).get("proxyCanvasPx", 128))
    scene = bs.configure_scene(studio, (proxy_canvas, proxy_canvas), str(out))
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
    root["designStage"] = recipe.get("designIntent", {}).get("status", "refinement_pass_02")
    root["targetSpriteHeightPx"] = int(recipe["sprite"]["targetHeightPx"])
    root["groundIncludedInAsset"] = False

    authored = build_machine(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material("ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0)))
    bs.add_box("ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0)

    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.16)
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
        print(f"[CH_GATE] soda machine V2 preflight PASS: {preflight_path}")
        return

    proxy = scene_gate.render_proxy(
        scene=scene,
        authored=authored,
        output_path=out / "proxy_south.png",
        profile=profile,
        asset_id=recipe["assetId"],
        direction="south",
    )
    proxy["targetSpriteHeightPx"] = int(recipe["sprite"]["targetHeightPx"])
    proxy["designVersion"] = 2
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] soda machine V2 SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
