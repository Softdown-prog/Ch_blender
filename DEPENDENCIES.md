# CH Blender standalone dependencies

## Required and included

- `tools/ch_blender/` — orchestration, contracts, quality gates, jobs and tests.
- `tools/tycoon_photo_studio/` — canonical Blender scene builders, studio presets,
  render pipelines, post-processing and package validation used directly by CH Blender.
- `tools/blender_bake_runner.py` — bake orchestration compatibility entrypoint.
- `.github/actions/setup-ch-blender/` — pinned Blender 4.2.3 setup/cache action retained
  as part of the tool contract.

## Intentionally not activated during migration

The old City Horizon CH Blender worker workflows are not copied as active workflows.
They currently target GitHub-hosted `ubuntu-latest` runners and some optional job
families reference game-repository helpers such as Character Forge and animation preview.

The standalone repository should receive a dedicated Windows self-hosted workflow next,
so expensive Blender execution runs on the owner's PC instead of GitHub-hosted compute.

## Runtime boundary

CH Blender generates and validates production assets. Direct City Horizon runtime
mutation bridges remain outside this repository. Promotion into the game happens only
after visual and contract approval.
