# CH Blender standalone migration

CH Blender was migrated from `Softdown-prog/City-horizon-` so asset
production can run independently from the game repository.

## Included

- `tools/ch_blender/`: CLI, workers, contracts, preflight profiles,
  authoring tools, scripts, tests, jobs and production recipes/data.
- `tools/blender_bake_runner.py`: Blender bake orchestration.
- `docs/`: CH Blender and directly related asset/render/camera/
  authoring documentation selected from City Horizon.

## Deliberately excluded

These bridges write directly into City Horizon runtime state and are
intentionally not part of the standalone production copy:

- `tools/ch_blender/runtime_integrations/`
- `tools/ch_blender/runtime_promotions/`
- `tools/ch_blender/integrate_ice_cream_runtime.py`

Approved outputs should be promoted to City Horizon only after
visual and contract validation.
