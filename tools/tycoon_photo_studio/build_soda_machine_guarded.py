#!/usr/bin/env python3
"""Build the original City Horizon soda vending machine prop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

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
    front_y = -d * 0.5 - 0.012

    box("SodaBase", (0, 0, base_h * 0.5), (w * 0.96, d * 0.95, base_h), mats["dark"], 0.035, "soda.base", True)
    body = box("SodaBody", (0, 0, base_h + h * 0.5), (w, d, h), mats["body"], float(g["cornerBevel"]), "soda.body")

    # Slightly darker side panel gives the tiny sprite an immediately readable 3D volume.
    box("SidePanel", (w * 0.505, 0.01, base_h + h * 0.51), (0.035, d * 0.88, h * 0.91), mats["side"], 0.012, "soda.side")

    marquee_h = float(g["marqueeHeight"])
    box(
        "TopMarquee", (0, front_y, base_h + h - marquee_h * 0.62),
        (w * 0.90, 0.055, marquee_h), mats["cream"], 0.035, "soda.marquee"
    )
    # Original CH wave emblem: three simple bars, not a real-world brand/logo.
    box("MarqueeStripeA", (-0.18, front_y - 0.031, base_h + h - marquee_h * 0.60), (0.28, 0.022, 0.055), mats["accent"], 0.015, "soda.graphic")
    box("MarqueeStripeB", (0.08, front_y - 0.032, base_h + h - marquee_h * 0.49), (0.30, 0.022, 0.055), mats["display"], 0.015, "soda.graphic")

    display_w = float(g["displayWidth"])
    display_h = float(g["displayHeight"])
    display_z = base_h + h * 0.62
    box("DisplayFrame", (-0.08, front_y - 0.012, display_z), (display_w + 0.08, 0.055, display_h + 0.08), mats["dark"], 0.028, "soda.display_frame")
    box("DisplayGlass", (-0.08, front_y - 0.045, display_z), (display_w, 0.035, display_h), mats["display"], 0.022, "soda.display")

    # Three oversized bottle silhouettes so the product still reads around 60 px tall.
    bottle_x = (-0.29, -0.08, 0.13)
    bottle_mats = (mats["bottleGreen"], mats["cream"], mats["bottleBlue"])
    for i, (x, mat) in enumerate(zip(bottle_x, bottle_mats)):
        box(f"BottleBody_{i}", (x, front_y - 0.067, display_z - 0.02), (0.12, 0.018, 0.28), mat, 0.035, "soda.product")
        box(f"BottleCap_{i}", (x, front_y - 0.070, display_z + 0.165), (0.065, 0.018, 0.05), mats["metal"], 0.015, "soda.product")

    control_x = w * 0.34
    control_z = base_h + h * 0.53
    box("ControlPanel", (control_x, front_y - 0.024, control_z), (float(g["controlWidth"]), 0.06, float(g["controlHeight"])), mats["cream"], 0.025, "soda.controls")
    for i in range(3):
        box(f"SelectButton_{i}", (control_x, front_y - 0.064, control_z + 0.13 - i * 0.13), (0.09, 0.025, 0.065), mats["accent"] if i == 0 else mats["metal"], 0.018, "soda.controls")

    vend_w = float(g["vendWidth"])
    vend_h = float(g["vendHeight"])
    vend_z = base_h + h * 0.22
    box("VendBayFrame", (-0.08, front_y - 0.012, vend_z), (vend_w + 0.10, 0.060, vend_h + 0.10), mats["cream"], 0.028, "soda.vend")
    box("VendBay", (-0.08, front_y - 0.052, vend_z), (vend_w, 0.045, vend_h), mats["dark"], 0.026, "soda.vend")

    # Coin return / service detail, deliberately chunky for pixel readability.
    box("CoinReturn", (control_x, front_y - 0.058, base_h + h * 0.30), (0.10, 0.03, 0.12), mats["dark"], 0.018, "soda.controls")
    box("LowerAccent", (0, front_y - 0.024, base_h + h * 0.085), (w * 0.76, 0.035, 0.06), mats["accent"], 0.018, "soda.trim")

    return authored


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    if recipe.get("contract") != "CH_PROP_SODA_MACHINE_V1":
        raise RuntimeError("Expected CH_PROP_SODA_MACHINE_V1 recipe")

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
    root["designStage"] = "blockout_pass_01"
    root["targetSpriteHeightPx"] = int(recipe["sprite"]["targetHeightPx"])
    root["groundIncludedInAsset"] = False

    authored = build_machine(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material("ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0)))
    bs.add_box("ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0)

    # Tight framing is intentional: final runtime sprite is only 60 px tall.
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
        print(f"[CH_GATE] soda machine preflight PASS: {preflight_path}")
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
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")
    save_blend(args.save_blend)
    print(f"[CH_GATE] soda machine SOUTH proxy ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
