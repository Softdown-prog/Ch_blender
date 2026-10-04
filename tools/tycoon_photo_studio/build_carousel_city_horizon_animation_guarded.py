#!/usr/bin/env python3
"""Bake City Horizon carousel rotation + horse vertical motion in four directions."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
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
import build_carousel_city_horizon_guarded as carousel  # noqa: E402


HORSE_PART_RE = re.compile(r"^Horse(?:Body|Chest|Neck|Head|Muzzle|Ear|Leg|Saddle)_(\d{2})")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_still(scene, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {
        "file": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def main():
    args = carousel.parse_args()
    recipe = carousel.load_json(args.recipe)
    if recipe.get("contract") != "CH_CAROUSEL_FRESH_V1":
        raise RuntimeError("Expected CH_CAROUSEL_FRESH_V1 recipe")

    animation = recipe.get("animationPlan", {})
    if not animation.get("enabled") or animation.get("contract") != "CH_CAROUSEL_ANIMATION_V1":
        raise RuntimeError("Carousel recipe must enable CH_CAROUSEL_ANIMATION_V1")

    frame_count = int(animation.get("frameCount", 48))
    if frame_count < 2 or frame_count > 96:
        raise RuntimeError("animation frameCount must be between 2 and 96")
    frame_duration_ms = int(animation.get("frameDurationMs", 100))
    rotation_radians = math.radians(float(animation.get("rotationDegreesPerLoop", 360.0)))
    bob_amplitude = float(animation.get("horseBobAmplitude", 0.14))
    bob_cycles = float(animation.get("horseBobCyclesPerLoop", 2.0))
    static_names = set(animation.get("staticObjects", ["PlinthLower", "PlinthMiddle", "CenterMast"]))
    requested_directions = list(animation.get("directions", ["south", "east", "west", "north"]))

    studio = bs.load_json(args.studio_preset)
    profile = scene_gate.load_profile(args.preflight_profile)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bs.clear_scene()
    source_res = tuple(map(int, studio["render"]["sourceResolution"]))
    scene = bs.configure_scene(studio, source_res, str(out))
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    mats = carousel.make_materials(recipe)
    root = fw.empty("AssetRoot")
    root["assetId"] = recipe["assetId"]
    root["assetType"] = recipe["assetType"]
    root["cameraContract"] = "CH_CAMERA_V1"
    root["studioPreset"] = "CH_TYCOON_STUDIO_V1"
    root["groundIncludedInAsset"] = False
    root["runtimeRepresentation"] = "2D_RGBA_pre_rendered_sprite_sequence"
    root["proceduralContract"] = recipe["contract"]
    root["qualityGateContract"] = "CH_SCENE_PREFLIGHT_V1"
    root["animationContract"] = animation["contract"]
    root["animationFrameCount"] = frame_count
    root["designStage"] = "animation_pass_01"
    root["legacyCarouselReuse"] = False

    authored = carousel.build_carousel(root, recipe, mats)

    receiver = studio["shadowReceiver"]
    receiver_mat = bs.make_material(
        "ShadowReceiver", receiver["materialColor"], float(receiver.get("roughness", 1.0))
    )
    bs.add_box(
        "ShadowReceiverPlane", receiver["location"], receiver["dimensions"], receiver_mat, 0.0
    )

    # Nested motion root lets the four camera directions remain independent from ride rotation.
    motion_root = fw.empty("CarouselMotionRoot")
    motion_root.parent = root
    motion_root["role"] = "carousel.motion_root"

    for obj in list(bpy.data.objects):
        if obj.parent == root and obj not in {motion_root} and obj.name not in static_names:
            obj.parent = motion_root

    # Cache neutral local Z for every horse body part. Poles rotate but do not bob.
    horse_parts: dict[int, list[tuple[object, float]]] = {}
    for obj in bpy.data.objects:
        match = HORSE_PART_RE.match(obj.name)
        if not match:
            continue
        horse_index = int(match.group(1))
        horse_parts.setdefault(horse_index, []).append((obj, float(obj.location.z)))

    if not horse_parts:
        raise RuntimeError("Animation baker found no horse body parts")

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
        carousel.save_blend(args.save_blend)
        print(f"[CH_GATE] carousel animation preflight PASS: {preflight_path}")
        return

    direction_map = {direction["id"]: direction for direction in bs.DIRECTIONS}
    missing = [direction for direction in requested_directions if direction not in direction_map]
    if missing:
        raise RuntimeError(f"Unknown animation directions: {missing}")

    def apply_frame(frame_index: int):
        progress = frame_index / frame_count
        motion_root.rotation_euler[2] = rotation_radians * progress
        for horse_index, parts in horse_parts.items():
            # Alternate neighboring mounts, plus a small distributed phase offset.
            phase = math.pi * (horse_index % 2) + (2.0 * math.pi * (horse_index % 7) / 7.0)
            bob = bob_amplitude * math.sin(2.0 * math.pi * bob_cycles * progress + phase)
            for obj, neutral_z in parts:
                obj.location.z = neutral_z + bob
        bpy.context.view_layer.update()

    manifest = {
        "contract": "CH_CAROUSEL_ANIMATION_FRAMES_V1",
        "status": "ok",
        "assetId": recipe["assetId"],
        "frameCount": frame_count,
        "frameDurationMs": frame_duration_ms,
        "loop": bool(animation.get("loop", True)),
        "rotationDegreesPerLoop": float(animation.get("rotationDegreesPerLoop", 360.0)),
        "horseBobAmplitude": bob_amplitude,
        "horseBobCyclesPerLoop": bob_cycles,
        "directions": requested_directions,
        "frames": {},
    }

    # SOUTH frame 000 is also the guarded proxy expected by agent_worker.py.
    bs.set_direction(root, direction_map[requested_directions[0]])
    apply_frame(0)
    proxy = scene_gate.render_proxy(
        scene=scene,
        authored=authored,
        output_path=out / "proxy_south.png",
        profile=profile,
        asset_id=recipe["assetId"],
        direction="south",
    )
    proxy["animationContract"] = animation["contract"]
    proxy["animationFrame"] = 0
    (out / "proxy_report.json").write_text(json.dumps(proxy, indent=2), encoding="utf-8")

    for direction_id in requested_directions:
        direction = direction_map[direction_id]
        bs.set_direction(root, direction)
        direction_dir = out / "frames" / direction_id
        direction_dir.mkdir(parents=True, exist_ok=True)
        frame_records = []

        for frame_index in range(frame_count):
            apply_frame(frame_index)
            target = direction_dir / f"frame_{frame_index:03d}.png"
            if direction_id == "south" and frame_index == 0:
                shutil.copy2(out / "proxy_south.png", target)
                record = {
                    "file": target.name,
                    "sha256": sha256(target),
                    "bytes": target.stat().st_size,
                }
            else:
                record = render_still(scene, target)
            record["frame"] = frame_index
            record["rotationDegrees"] = 360.0 * frame_index / frame_count
            frame_records.append(record)
            print(f"[CH_ANIM] {direction_id} frame {frame_index + 1:02d}/{frame_count:02d}")

        manifest["frames"][direction_id] = frame_records

    # Restore canonical neutral state for optional .blend inspection.
    bs.set_direction(root, direction_map["south"])
    motion_root.rotation_euler[2] = 0.0
    for parts in horse_parts.values():
        for obj, neutral_z in parts:
            obj.location.z = neutral_z
    bpy.context.view_layer.update()

    manifest_path = out / "animation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    carousel.save_blend(args.save_blend)
    print(f"[CH_GATE] carousel animation frames ready: {manifest_path}")


if __name__ == "__main__":
    main()
