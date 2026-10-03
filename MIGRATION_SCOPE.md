# CH Blender standalone migration

This repository contains the CH Blender production tool migrated from
`Softdown-prog/City-horizon-`.

## Source copied

- `tools/ch_blender/` — CH Blender CLI, workers, contracts, profiles,
  scripts, tests, jobs and authoring data.
- `tools/blender_bake_runner.py` — Blender bake orchestration used by
  the production pipeline.
- `docs/` — documentation directly related to CH Blender, asset
  production, render quality, camera/authoring contracts and the
  amusement-ride production pipeline.

## Intentionally not copied

Direct City Horizon runtime mutation bridges are excluded from the
standalone production repository:

- `tools/ch_blender/runtime_integrations/`
- `tools/ch_blender/runtime_promotions/`
- `tools/ch_blender/integrate_ice_cream_runtime.py`

Approved outputs should be promoted to City Horizon explicitly after
visual/contract validation instead of CH Blender modifying game
runtime files directly.
