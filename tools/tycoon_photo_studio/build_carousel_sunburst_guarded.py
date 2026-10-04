"""Original City Horizon Sunburst Pavilion carousel proxy builder.

This design keeps only broad fairground language from classic tycoon-era references:
a low/open round ride and a high-contrast radial canopy. Geometry, trim hierarchy,
palette accents and the crown are authored as a distinct City Horizon asset.
"""
from __future__ import annotations

import argparse
import json
import math
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
import scene_gate  # noqa: E402
import build_carousel_classic_guarded as classic  # noqa: E402
import build_carousel_city_horizon_v4_guarded as v4  # noqa: E402


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


def _mat(name):
    material = bpy.data.materials.get(f"Carousel_{name}")
    if material is None:
        raise RuntimeError(f"Missing Sunburst carousel material: {name}")
    return material


def _motion(obj):
    obj["runtimeLayer"] = "motion_overlay"
    return obj


def _build_sun_crown(rotor, geo):
    """Small jewel-like crown unique to the Sunburst Pavilion design."""
    gold = _mat("gold")
    teal = _mat("teal")
    burgundy = _mat("burgundy")
    inner_z = float(geo["canopyInnerZ"])
    crown_z = inner_z + 0.50

    crown = classic._empty("SunburstCrown", rotor)
    added = []
    mast = classic._cylinder(
        "SunburstCrownMast", crown, (0.0, 0.0, inner_z + 0.27),
        0.055, 0.58, gold, vertices=16
    )
    added.append(_motion(mast))

    hub = classic._sphere(
        "SunburstCrownHub", crown, (0.0, 0.0, crown_z),
        (0.13, 0.13, 0.13), burgundy, segments=18, rings=10
    )
    added.append(_motion(hub))

    # Eight rounded jewels form a crown rather than copying a horse/pole ornament.
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        r = 0.19
        jewel = classic._sphere(
            f"SunburstCrownJewel_{i:02d}", crown,
            (r * math.cos(a), r * math.sin(a), crown_z + 0.015 * (i % 2)),
            (0.075, 0.075, 0.095), gold if i % 2 == 0 else teal,
            segments=14, rings=8,
        )
        added.append(_motion(jewel))

    finial = classic._sphere(
        "SunburstCrownFinial", crown, (0.0, 0.0, crown_z + 0.27),
        (0.09, 0.09, 0.12), gold, segments=16, rings=9
    )
    added.append(_motion(finial))
    return added


def build_scene(recipe, studio, out):
    scene, root, rotor, ground, authored = v4.build_scene(recipe, studio, out)
    added = _build_sun_crown(rotor, recipe["geometry"])
    authored = list(authored) + added
    bs.calibrate_ortho_scale(scene, authored, safety_margin=0.14)
    bs.set_direction(root, bs.DIRECTIONS[0])
    scene.frame_set(int(recipe["animation"].get("frameStart", 1)))
    bpy.context.view_layer.update()
    return scene, root, rotor, ground, authored


def main():
    args = parse_args()
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    if recipe.get("contract") != "CITY_HORIZON_CAROUSEL_V1":
        raise RuntimeError("Expected CITY_HORIZON_CAROUSEL_V1 recipe")
    if recipe.get("identity") != "sunburst_pavilion":
        raise RuntimeError("Sunburst builder requires identity=sunburst_pavilion")

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
        classic._save_blend(args.save_blend)
        print(f"[CH_GATE] Sunburst Pavilion preflight PASS: {preflight_path}")
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
    classic._save_blend(args.save_blend)
    print(f"[CH_GATE] Sunburst Pavilion proxy SOUTH ready: {proxy['sha256']}")


if __name__ == "__main__":
    main()
