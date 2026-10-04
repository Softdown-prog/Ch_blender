#!/usr/bin/env python3
"""Final refinement wrapper for the City Horizon pink flowering tree.

Keeps the established broadleaf-V5 Blender builder, but applies three small
runtime-readability corrections for pass 06: controlled canopy windows,
slightly shorter trunk via recipe values, and a lighter crown interior palette.
"""
from __future__ import annotations

import math
import random

from mathutils import Euler, Vector

import build_pink_flowering_tree_guarded as base


def _inside_window(p, g):
    crown_w = float(g["crownWidth"])
    crown_d = float(g["crownDepth"])
    crown_h = float(g["crownHeight"])
    crown_z = float(g["crownCenterZ"])
    for window in g.get("canopyWindows", []):
        cx, cy, cz = map(float, window["center"])
        rx, ry, rz = map(float, window["radius"])
        center = Vector((cx * crown_w, cy * crown_d, crown_z + cz * crown_h))
        sx = max(0.001, rx * crown_w)
        sy = max(0.001, ry * crown_d)
        sz = max(0.001, rz * crown_h)
        qx = (p.x - center.x) / sx
        qy = (p.y - center.y) / sy
        qz = (p.z - center.z) / sz
        if qx * qx + qy * qy + qz * qz < 1.0:
            return True
    return False


def scatter_defined_leaves(groups, recipe, mats, rng, root, authored):
    g = recipe["geometry"]
    meshes = {
        "back": base.make_leaf_mesh("PinkLeafPlumMesh", mats["leafBack"], g["leafOutlineSegments"], g["leafThickness"]),
        "mid": base.make_leaf_mesh("PinkLeafBerryMesh", mats["leafMid"], g["leafOutlineSegments"], g["leafThickness"]),
        "front": base.make_leaf_mesh("PinkLeafRoseMesh", mats["leafFront"], g["leafOutlineSegments"], g["leafThickness"]),
        "highlight": base.make_leaf_mesh("PinkLeafLilacMesh", mats["leafHighlight"], g["leafOutlineSegments"], g["leafThickness"]),
        "warm": base.make_leaf_mesh("PinkLeafWarmMesh", mats["leafWarm"], g["leafOutlineSegments"], g["leafThickness"]),
    }
    lmin = float(g["leafLengthMin"])
    lmax = float(g["leafLengthMax"])
    wr_min = float(g["leafWidthRatioMin"])
    wr_max = float(g["leafWidthRatioMax"])

    leaf_index = 0
    skipped_for_windows = 0
    for _gi, (depth, center) in enumerate(groups):
        if depth == 0:
            count = int(g["leavesPerRearGroup"])
            spread = Vector((0.82, 0.60, 0.50))
        elif depth == 1:
            count = int(g["leavesPerMidGroup"])
            spread = Vector((0.90, 0.67, 0.57))
        else:
            count = int(g["leavesPerFrontGroup"])
            spread = Vector((0.94, 0.70, 0.61))

        for _li in range(count):
            for _ in range(12):
                dx = rng.uniform(-1.0, 1.0)
                dy = rng.uniform(-1.0, 1.0)
                dz = rng.uniform(-1.0, 1.0)
                if dx * dx + dy * dy + dz * dz <= 1.0:
                    break
            p = center + Vector((dx * spread.x, dy * spread.y, dz * spread.z))

            # Keep the rear support layer so the crown remains visually full,
            # but remove selected mid/front leaves to expose real branches.
            if depth > 0 and _inside_window(p, g):
                skipped_for_windows += 1
                continue

            if depth == 0:
                key = "back" if rng.random() < .60 else "mid"
            elif depth == 1:
                roll = rng.random()
                key = "mid" if roll < .52 else ("front" if roll < .90 else "highlight")
            else:
                roll = rng.random()
                key = "front" if roll < .55 else ("highlight" if roll < .91 else "mid")
                if rng.random() < .025:
                    key = "warm"

            length = rng.uniform(lmin, lmax) * (0.94 if depth == 0 else 1.0)
            ratio = rng.uniform(wr_min, wr_max)
            yaw = math.atan2(p.y, p.x) + rng.uniform(-0.72, 0.72)
            pitch = rng.uniform(-0.52, 0.52)
            roll = rng.uniform(-0.62, 0.62)
            base.add_leaf(
                f"DefinedLeaf_{leaf_index:04d}", meshes[key], p, length, ratio,
                Euler((roll, pitch, yaw)), root, authored,
            )
            leaf_index += 1

    root["canopyWindowSkippedLeaves"] = skipped_for_windows
    return leaf_index


base.scatter_defined_leaves = scatter_defined_leaves

if __name__ == "__main__":
    base.main()
