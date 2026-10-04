"""Safe orthographic camera depth adjustment for large CH Blender assets."""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

import build_scene as bs
from render_geometry import scene_studio_state


def ensure_positive_camera_depth(scene, authored, *, root=None, minimum_depth=2.0):
    """Move the camera backward along its own optical axis if geometry reaches it.

    This does not alter orthographic X/Y framing, camera rotation, yaw or elevation.
    It only increases camera-to-asset depth so world_to_camera_view reports positive Z.
    """
    cam = scene.camera
    if cam is None:
        return 0.0

    root = root or bpy.data.objects.get("AssetRoot")
    original_z = root.rotation_euler[2] if root is not None else 0.0
    min_depth = float("inf")

    try:
        for direction in bs.DIRECTIONS:
            if root is not None:
                root.rotation_euler[2] = math.radians(direction["rotationDegrees"])
                bpy.context.view_layer.update()
            inv = cam.matrix_world.inverted()
            deps = bpy.context.evaluated_depsgraph_get()
            for obj in authored:
                if obj.type != "MESH" or obj.hide_render:
                    continue
                evaluated = obj.evaluated_get(deps)
                for corner in evaluated.bound_box:
                    local = inv @ (evaluated.matrix_world @ Vector(corner))
                    min_depth = min(min_depth, -local.z)
    finally:
        if root is not None:
            root.rotation_euler[2] = original_z
            bpy.context.view_layer.update()

    if min_depth == float("inf") or min_depth >= minimum_depth:
        return 0.0

    dolly = (minimum_depth - min_depth) + 1.0
    backward = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, 1.0))
    cam.location += backward * dolly
    bpy.context.view_layer.update()

    # Axial translation is projection-neutral for an orthographic camera. Refresh the
    # stored studio state so subsequent drift checks still protect against real changes.
    scene["ch.studioState"] = scene_studio_state(scene)
    print(f"[camera_depth] dolly={dolly:.3f} BU minDepthBefore={min_depth:.3f}")
    return dolly
