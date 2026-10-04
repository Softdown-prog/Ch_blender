#!/usr/bin/env python3
"""Pink flowering tree proxy using CH Texture Forge bark_broadleaf_01 on woody parts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
TEXTURE_FORGE = REPO_ROOT / "tools" / "ch_texture_forge"
if str(TEXTURE_FORGE) not in sys.path:
    sys.path.insert(0, str(TEXTURE_FORGE))

import ch_texture_forge as texture_forge  # noqa: E402
import build_pink_flowering_tree_refine_guarded as refine  # noqa: E402

base = refine.base
ORIGINAL_MAKE_MATERIALS = base.make_materials
TEXTURE_PACK = TEXTURE_FORGE / "recipes" / "core_pack_v1.json"
TEXTURE_ID = "bark_broadleaf_01"


def _texture_spec():
    pack = json.loads(TEXTURE_PACK.read_text(encoding="utf-8"))
    for spec in pack.get("textures", []):
        if spec.get("id") == TEXTURE_ID:
            return spec
    raise RuntimeError(f"CH_TEXTURE_NOT_FOUND: {TEXTURE_ID}")


def _image(name, size, pixels, colorspace="sRGB"):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True, float_buffer=False)
    image.pixels.foreach_set(pixels)
    image.pack()
    image.colorspace_settings.name = colorspace
    return image


def _apply_bark(mat, base_img, rough_img, height_img, strength=0.16):
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"CH_BARK_MATERIAL_NO_BSDF: {mat.name}")

    texcoord = tree.nodes.new("ShaderNodeTexCoord")
    texcoord.label = "CH Texture Forge generated coordinates"
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.35, 1.35, 2.8)

    base_node = tree.nodes.new("ShaderNodeTexImage")
    base_node.image = base_img
    base_node.extension = "REPEAT"
    base_node.interpolation = "Linear"

    rough_node = tree.nodes.new("ShaderNodeTexImage")
    rough_node.image = rough_img
    rough_node.extension = "REPEAT"
    rough_node.interpolation = "Linear"

    height_node = tree.nodes.new("ShaderNodeTexImage")
    height_node.image = height_img
    height_node.extension = "REPEAT"
    height_node.interpolation = "Linear"

    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.075

    tree.links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    for node in (base_node, rough_node, height_node):
        tree.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
    tree.links.new(base_node.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])
    tree.links.new(height_node.outputs["Color"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    mat["chTextureForgeId"] = TEXTURE_ID
    mat["chTextureForgeExternalVisualInputs"] = "[]"
    mat["chTextureForgeProvenance"] = "100% procedural CH Texture Forge"


def make_materials(recipe):
    mats = ORIGINAL_MAKE_MATERIALS(recipe)
    spec = _texture_spec()
    size, base_pixels, rough_pixels, height_pixels = texture_forge.make_pixels(spec)
    base_img = _image("CH_BarkBroadleaf01_BaseColor", size, base_pixels, "sRGB")
    rough_img = _image("CH_BarkBroadleaf01_Roughness", size, rough_pixels, "Non-Color")
    height_img = _image("CH_BarkBroadleaf01_Height", size, height_pixels, "Non-Color")
    _apply_bark(mats["trunkWarm"], base_img, rough_img, height_img, 0.18)
    _apply_bark(mats["trunkDark"], base_img, rough_img, height_img, 0.12)
    return mats


base.make_materials = make_materials

if __name__ == "__main__":
    base.main()
