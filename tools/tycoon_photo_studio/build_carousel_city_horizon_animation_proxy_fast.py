#!/usr/bin/env python3
"""Fast review wrapper for the carousel animation baker.

Keeps the guarded SOUTH proxy at normal review quality, then forces the raw
animation sequence to 384x384 / 2 Cycles samples so 192 preview frames can
finish on the Windows CPU runner in a practical amount of time.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_carousel_city_horizon_animation_guarded as target  # noqa: E402

_original_render_still = target.render_still


def fast_render_still(scene, path):
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 2
        scene.cycles.use_denoising = False
    return _original_render_still(scene, path)


target.render_still = fast_render_still

if __name__ == "__main__":
    target.main()
