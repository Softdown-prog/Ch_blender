# CH Texture Forge V1

CH Texture Forge is the procedural texture layer for City Horizon / CH Blender.

## Goal

Generate deterministic, tileable texture maps without incorporating photos, downloaded textures, HDRIs or third-party visual assets. The generator owns the full visual recipe and records provenance in every output manifest.

## Current families

- `wood`
- `stone`
- `concrete`
- `asphalt`
- `painted_metal`
- `bark`

The first pack is `recipes/core_pack_v1.json` at 256x256. Each recipe has its own seed and palette.

## Output

For each texture id the forge writes:

- `<id>_basecolor.png`
- `<id>_roughness.png`
- `<id>_height.png`
- `manifest.json`

The pack also writes `texture_forge_report.json`.

Each manifest declares `tileable: true`, `externalVisualInputs: []` and `provenance: 100% procedural CH Texture Forge`.

## Run with CH Blender

```powershell
blender.exe --background --python tools/ch_texture_forge/ch_texture_forge.py -- --recipe tools/ch_texture_forge/recipes/core_pack_v1.json --output out/ch_texture_forge/core_pack_v1
```

To render a single recipe from the pack:

```powershell
blender.exe --background --python tools/ch_texture_forge/ch_texture_forge.py -- --recipe tools/ch_texture_forge/recipes/core_pack_v1.json --output out/ch_texture_forge/core_pack_v1 --only wood_warm_01
```

## Design rules

1. No external visual inputs in the default procedural path.
2. Seeds make outputs reproducible.
3. Noise functions are periodic, so maps tile at texture boundaries.
4. Base color, roughness and height are generated from the same source field to keep materials coherent.
5. Normal-map baking and direct material-node integration are planned as the next layer; height is already emitted for that conversion.
