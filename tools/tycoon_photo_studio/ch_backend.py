"""Blender-side backend detection shared by scene and mask rendering."""
import os,json
from pathlib import Path
import bpy

def legacy_cpu_backend():
    # The worker sets identity from the executable marker; direct bpy use reads it too.
    if os.environ.get("CH_BLENDER_BACKEND") == "legacy_cpu_4_2_3":
        return True
    marker = Path(bpy.app.binary_path).parent / "ch-legacy-build.json"
    if not marker.is_file():
        return False
    info = json.loads(marker.read_text(encoding="utf-8-sig"))
    return info.get("backend") == "legacy_cpu_4_2_3" and info.get("upstreamTag") == "v4.2.3"
