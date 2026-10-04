#!/usr/bin/env python3
"""CH Texture Forge V1.

Deterministic, tileable, 100% procedural texture generator for City Horizon.
No photos, downloaded textures, HDRIs or third-party visual assets are used.
Run with Blender Python so PNG writing is handled by bpy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy

CONTRACT = "CH_TEXTURE_FORGE_V1"
TAU = math.tau


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--recipe", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--only", default="", help="Optional recipe id")
    return p.parse_args(argv)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clamp01(v):
    return max(0.0, min(1.0, float(v)))


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    return t * t * (3.0 - 2.0 * t)


def hash2(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 69069) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFF) / float(0xFFFFFF)


def periodic_value_noise(x, y, cells, seed):
    """Tileable value noise over normalized UV coordinates."""
    cells = max(1, int(cells))
    px = x * cells
    py = y * cells
    x0 = math.floor(px)
    y0 = math.floor(py)
    tx = smooth(px - x0)
    ty = smooth(py - y0)
    x1 = x0 + 1
    y1 = y0 + 1
    a = hash2(x0 % cells, y0 % cells, seed)
    b = hash2(x1 % cells, y0 % cells, seed)
    c = hash2(x0 % cells, y1 % cells, seed)
    d = hash2(x1 % cells, y1 % cells, seed)
    return lerp(lerp(a, b, tx), lerp(c, d, tx), ty)


def fbm(u, v, seed, base_cells=4, octaves=5, persistence=.52):
    amp = 1.0
    total = 0.0
    norm = 0.0
    cells = max(1, int(base_cells))
    for i in range(max(1, int(octaves))):
        total += periodic_value_noise(u, v, cells, seed + i * 1013) * amp
        norm += amp
        amp *= persistence
        cells *= 2
    return total / norm if norm else 0.0


def ridge(v):
    return 1.0 - abs(2.0 * v - 1.0)


def color_mix(a, b, t):
    return tuple(lerp(a[i], b[i], clamp01(t)) for i in range(3))


def family_sample(family, u, v, seed, p):
    n = fbm(u, v, seed, p.get("baseCells", 4), p.get("octaves", 5), p.get("persistence", .52))
    fine = fbm(u, v, seed + 3001, p.get("fineCells", 18), 3, .48)

    if family == "wood":
        grain_scale = float(p.get("grainScale", 13.0))
        warp = (n - .5) * float(p.get("warp", 1.5))
        grain = .5 + .5 * math.sin(TAU * (v * grain_scale + warp))
        knots = ridge(fbm(u, v, seed + 77, 3, 4, .5))
        h = clamp01(.58 * grain + .28 * fine + .14 * knots)
        rough = clamp01(.46 + .28 * (1.0 - h))
        return h, rough

    if family == "stone":
        blocks = ridge(periodic_value_noise(u, v, int(p.get("cells", 7)), seed + 91))
        h = clamp01(.58 * n + .30 * blocks + .12 * fine)
        rough = clamp01(.66 + .22 * fine)
        return h, rough

    if family == "concrete":
        pores = ridge(fine)
        h = clamp01(.74 * n + .26 * pores)
        rough = clamp01(.72 + .18 * (1.0 - fine))
        return h, rough

    if family == "asphalt":
        aggregate = ridge(fbm(u, v, seed + 113, 24, 3, .55))
        h = clamp01(.45 * n + .55 * aggregate)
        rough = clamp01(.78 + .16 * aggregate)
        return h, rough

    if family == "painted_metal":
        orange = ridge(fbm(u, v, seed + 157, 10, 4, .55))
        h = clamp01(.70 * n + .30 * orange)
        rough = clamp01(.28 + .30 * orange)
        return h, rough

    if family == "bark":
        vertical = .5 + .5 * math.sin(TAU * (u * float(p.get("ridgeScale", 10.0)) + (n - .5) * 1.8))
        cracks = ridge(fbm(u, v, seed + 211, 12, 4, .58))
        h = clamp01(.57 * vertical + .30 * cracks + .13 * fine)
        rough = clamp01(.70 + .20 * cracks)
        return h, rough

    raise ValueError(f"Unsupported family: {family}")


def make_pixels(spec):
    size = int(spec.get("size", 256))
    seed = int(spec.get("seed", 1))
    family = spec["family"]
    params = spec.get("params", {})
    palette = spec.get("palette", {})
    dark = tuple(palette.get("dark", [0.20, 0.20, 0.20]))
    light = tuple(palette.get("light", [0.70, 0.70, 0.70]))
    accent = tuple(palette.get("accent", light))

    base = [0.0] * (size * size * 4)
    rough = [0.0] * (size * size * 4)
    height = [0.0] * (size * size * 4)

    for y in range(size):
        v = y / size
        for x in range(size):
            u = x / size
            h, r = family_sample(family, u, v, seed, params)
            accent_mask = clamp01((h - .62) * 2.6)
            col = color_mix(dark, light, h)
            col = color_mix(col, accent, accent_mask * float(params.get("accentStrength", .18)))
            idx = (y * size + x) * 4
            base[idx:idx+4] = [clamp01(col[0]), clamp01(col[1]), clamp01(col[2]), 1.0]
            rough[idx:idx+4] = [r, r, r, 1.0]
            height[idx:idx+4] = [h, h, h, 1.0]
    return size, base, rough, height


def save_png(path, size, pixels, name):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True, float_buffer=False)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(spec, output_root):
    if spec.get("contract") != CONTRACT:
        raise RuntimeError(f"Expected {CONTRACT}")
    tex_id = spec["id"]
    out = output_root / tex_id
    out.mkdir(parents=True, exist_ok=True)
    size, base, rough, height = make_pixels(spec)
    files = {
        "baseColor": out / f"{tex_id}_basecolor.png",
        "roughness": out / f"{tex_id}_roughness.png",
        "height": out / f"{tex_id}_height.png",
    }
    save_png(files["baseColor"], size, base, f"{tex_id}_base")
    save_png(files["roughness"], size, rough, f"{tex_id}_rough")
    save_png(files["height"], size, height, f"{tex_id}_height")
    manifest = {
        "contract": "CH_TEXTURE_OUTPUT_V1",
        "status": "ok",
        "id": tex_id,
        "family": spec["family"],
        "seed": int(spec.get("seed", 1)),
        "size": size,
        "tileable": True,
        "externalVisualInputs": [],
        "provenance": "100% procedural CH Texture Forge",
        "maps": {k: {"file": v.name, "sha256": sha256(v)} for k, v in files.items()},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    args = parse_args()
    recipe = load_json(args.recipe)
    specs = recipe.get("textures", [recipe])
    if args.only:
        specs = [s for s in specs if s.get("id") == args.only]
        if not specs:
            raise RuntimeError(f"Texture id not found: {args.only}")
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    results = [generate(spec, root) for spec in specs]
    report = {
        "contract": "CH_TEXTURE_FORGE_REPORT_V1",
        "status": "ok",
        "count": len(results),
        "outputs": results,
    }
    (root / "texture_forge_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[CH_TEXTURE_FORGE] generated {len(results)} tileable procedural textures")


if __name__ == "__main__":
    main()
