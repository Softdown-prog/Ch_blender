#!/usr/bin/env python3
"""Fast guarded wrapper for carousel primary color-mask animation.

The mask pass intentionally changes world/material render state after normal
preflight. Refresh the studio-state checksum only for that deliberate transition,
then keep all later direction changes protected by the normal drift guard.
Mask sequence renders use one Cycles sample because the pass is binary emission.
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_carousel_city_horizon_primary_mask_guarded as target  # noqa: E402
from render_geometry import scene_studio_state  # noqa: E402

_original_set_direction = target.bs.set_direction
_original_render_still = target.render_still
_refreshed_after_mask_setup = False


def mask_set_direction(root, direction):
    global _refreshed_after_mask_setup
    try:
        return _original_set_direction(root, direction)
    except RuntimeError as exc:
        if "CH_STUDIO_DRIFT" not in str(exc) or _refreshed_after_mask_setup:
            raise
        scene = bpy.context.scene
        scene["ch.studioState"] = scene_studio_state(scene)
        _refreshed_after_mask_setup = True
        print("[CH_MASK] accepted intentional mask render-state transition")
        return _original_set_direction(root, direction)


def fast_mask_render(scene, path):
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 1
        scene.cycles.use_denoising = False
    return _original_render_still(scene, path)


target.bs.set_direction = mask_set_direction
target.render_still = fast_mask_render

if __name__ == "__main__":
    target.main()
